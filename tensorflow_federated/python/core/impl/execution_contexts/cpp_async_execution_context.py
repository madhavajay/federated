# Copyright 2022, The TensorFlow Federated Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A context for execution based on an embedded executor instance."""

import asyncio
import concurrent
import contextlib
import pprint
import textwrap
from typing import Set

from absl import logging

from pybind11_abseil import status as absl_status
from tensorflow_federated.python.common_libs import retrying
from tensorflow_federated.python.core.impl.context_stack import context_base
from tensorflow_federated.python.core.impl.execution_contexts import compiler_pipeline
from tensorflow_federated.python.core.impl.executors import cardinalities_utils
from tensorflow_federated.python.core.impl.executors import value_serialization
from tensorflow_federated.python.core.impl.types import type_conversions


def get_absl_retryable_error_codes() -> Set[absl_status.StatusCode]:
  """Returns Absl retryable error codes."""
  # TODO(b/237122326): Move this function into executors_errors when
  # absl_status works in OSS.
  return set([
      absl_status.StatusCode.UNAVAILABLE,
      absl_status.StatusCode.FAILED_PRECONDITION
  ])


# TODO(b/193900393): Define a custom error in CPP and expose to python to
# more easily localize and control retries.
def _is_retryable_absl_status(exception):
  return (isinstance(exception, absl_status.StatusNotOk) and
          exception.status.code() in get_absl_retryable_error_codes())


class AsyncSerializeAndExecuteCPPContext(context_base.Context):
  """An async execution context delegating to CPP Executor bindings."""

  def __init__(
      self,
      factory,
      compiler_fn,
      max_workers=None,
      *,
      cardinality_inference_fn: cardinalities_utils
      .CardinalityInferenceFnType = cardinalities_utils.infer_cardinalities):
    super().__init__()
    self._executor_factory = factory
    self._compiler_pipeline = compiler_pipeline.CompilerPipeline(compiler_fn)
    self._futures_executor_pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=max_workers)
    self._cardinality_inference_fn = cardinality_inference_fn

  @contextlib.contextmanager
  def _reset_factory_on_error(self, ex_factory, cardinalities):
    try:
      # We pass a copy down to prevent the caller from mutating.
      yield ex_factory.create_executor({**cardinalities})
    except Exception:
      ex_factory.clean_up_executor({**cardinalities})
      raise

  @retrying.retry(
      retry_on_exception_filter=_is_retryable_absl_status,
      wait_max_ms=300_000,  # 5 minutes.
      wait_multiplier=2,
  )
  async def invoke(self, comp, arg):
    compiled_comp = self._compiler_pipeline.compile(comp)
    serialized_comp, _ = value_serialization.serialize_value(
        compiled_comp, comp.type_signature)
    cardinalities = self._cardinality_inference_fn(
        arg, comp.type_signature.parameter)

    try:
      with self._reset_factory_on_error(self._executor_factory,
                                        cardinalities) as executor:
        fn = executor.create_value(serialized_comp)
        if arg is not None:
          try:
            serialized_arg, _ = value_serialization.serialize_value(
                arg, comp.type_signature.parameter)
          except Exception as e:
            raise TypeError(
                f'Failed to serialize argument:\n{arg}\nas a value of type:\n'
                f'{comp.type_signature.parameter}') from e
          arg_value = executor.create_value(serialized_arg)
          call = executor.create_call(fn.ref, arg_value.ref)
        else:
          call = executor.create_call(fn.ref, None)
        # Delaying grabbing the event loop til now ensures that the call below
        # is attached to the loop running the invoke.
        running_loop = asyncio.get_running_loop()
        result_pb = await running_loop.run_in_executor(
            self._futures_executor_pool, lambda: executor.materialize(call.ref))
    except absl_status.StatusNotOk as e:
      indent = lambda s: textwrap.indent(s, prefix='\t')
      if arg is None:
        arg_str = 'without any arguments'
      else:
        arg_str = f'with argument:\n{indent(pprint.pformat(arg))}'
      logging.error('Error invoking computation with signature:\n%s\n%s\n',
                    indent(comp.type_signature.formatted_representation()),
                    arg_str)
      logging.error('Error: \n%s', e.status.message())
      raise e
    result_value, _ = value_serialization.deserialize_value(
        result_pb, comp.type_signature.result)
    return type_conversions.type_to_py_container(result_value,
                                                 comp.type_signature.result)
