load("@rules_python//python:defs.bzl", "py_library", "py_test")

package(default_visibility = [
    ":cifar100_packages",
    "//tensorflow_federated/python/simulation:simulation_users",
])

package_group(
    name = "cifar100_packages",
    packages = ["//tensorflow_federated/python/simulation/baselines/cifar100/..."],
)

licenses(["notice"])

py_library(
    name = "cifar100",
    srcs = ["__init__.py"],
    srcs_version = "PY3",
    visibility = ["//tensorflow_federated/python/simulation/baselines:__pkg__"],
    deps = [":image_classification_tasks"],
)

py_library(
    name = "image_classification_preprocessing",
    srcs = ["image_classification_preprocessing.py"],
    srcs_version = "PY3",
    deps = ["//tensorflow_federated/python/simulation/baselines:client_spec"],
)

py_test(
    name = "image_classification_preprocessing_test",
    size = "medium",
    srcs = ["image_classification_preprocessing_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":image_classification_preprocessing",
        "//tensorflow_federated/python/core/backends/native:execution_contexts",
        "//tensorflow_federated/python/simulation/baselines:client_spec",
    ],
)

py_library(
    name = "image_classification_tasks",
    srcs = ["image_classification_tasks.py"],
    srcs_version = "PY3",
    deps = [
        ":image_classification_preprocessing",
        "//tensorflow_federated/python/learning:keras_utils",
        "//tensorflow_federated/python/learning:model",
        "//tensorflow_federated/python/simulation/baselines:baseline_task",
        "//tensorflow_federated/python/simulation/baselines:client_spec",
        "//tensorflow_federated/python/simulation/baselines:task_data",
        "//tensorflow_federated/python/simulation/datasets:cifar100",
        "//tensorflow_federated/python/simulation/datasets:client_data",
        "//tensorflow_federated/python/simulation/models:resnet_models",
    ],
)

py_test(
    name = "image_classification_tasks_test",
    srcs = ["image_classification_tasks_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":image_classification_tasks",
        "//tensorflow_federated/python/core/backends/native:execution_contexts",
        "//tensorflow_federated/python/simulation/baselines:baseline_task",
        "//tensorflow_federated/python/simulation/baselines:client_spec",
        "//tensorflow_federated/python/simulation/models:resnet_models",
    ],
)
