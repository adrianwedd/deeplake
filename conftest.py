import os
from uuid import uuid1

import pytest

from hub.constants import (MIN_LOCAL_CACHE_SIZE, MIN_MEMORY_CACHE_SIZE,
                           PYTEST_LOCAL_PROVIDER_BASE_ROOT,
                           PYTEST_MEMORY_PROVIDER_BASE_ROOT,
                           PYTEST_S3_PROVIDER_BASE_ROOT)
from hub.core.storage import LocalProvider, MemoryProvider, S3Provider
from hub.util.cache_chain import get_cache_chain


def _skip_if_none(val):
    if val is None:
        pytest.skip()


def _is_opt_true(request, opt):
    return request.config.getoption(opt)


def pytest_addoption(parser):
    parser.addoption(
        "--memory-skip",
        action="store_true",
        help="Tests using the `memory_provider` fixture will be skipped. Tests using the `storage` fixture will be skipped if called with \
                `MemoryProvider`.",
    )
    parser.addoption(
        "--local",
        action="store_true",
        help="Tests using the `storage`/`local_provider` fixtures will run with `LocalProvider`.",
    )
    parser.addoption(
        "--s3",
        action="store_true",
        help="Tests using the `storage`/`s3_provider` fixtures will run with `S3Provider`.",
    )
    parser.addoption(
        "--cache-chains",
        action="store_true",
        help="Tests using the `storage` fixture may run with combinations of all enabled providers \
                in cache chains. For example, if the option `--s3` is not provided, all cache chains that use `S3Provider` are skipped.",
    )
    parser.addoption(
        "--cache-chains-only",
        action="store_true",
        help="Force enables `--cache-chains`. `storage` fixture only returns cache chains. For example, if `--s3` is provided, \
            `storage` will never be just `S3Provider`.",
    )


@pytest.fixture(scope="session")
def memory_storage(request):
    if not _is_opt_true(request, "--memory-skip"):
        root = PYTEST_MEMORY_PROVIDER_BASE_ROOT
        return MemoryProvider(root)


@pytest.fixture(scope="session")
def local_storage(request):
    if _is_opt_true(request, "--local"):
        # TODO: root as option
        root = PYTEST_LOCAL_PROVIDER_BASE_ROOT
        return LocalProvider(root)


@pytest.fixture(scope="session")
def s3_storage(request):
    if _is_opt_true(request, "--s3"):
        # TODO: root as option
        root = PYTEST_S3_PROVIDER_BASE_ROOT
        return S3Provider(root)


@pytest.fixture(scope="session")
def storage(request, memory_storage, local_storage, s3_storage):
    requested_providers = request.param.split(",")

    # --cache-chains-only force enables --cache-chains
    use_cache_chains_only = _is_opt_true(request, "--cache-chains-only")
    use_cache_chains = _is_opt_true(request, "--cache-chains") or use_cache_chains_only

    if use_cache_chains_only and len(requested_providers) <= 1:
        pytest.skip()

    if not use_cache_chains and len(requested_providers) > 1:
        pytest.skip()

    storage_providers = []
    cache_sizes = []

    if "memory" in requested_providers:
        _skip_if_none(memory_storage)
        storage_providers.append(memory_storage)
        cache_sizes.append(MIN_MEMORY_CACHE_SIZE)
    if "local" in requested_providers:
        _skip_if_none(local_storage)
        storage_providers.append(local_storage)
        cache_sizes.append(MIN_LOCAL_CACHE_SIZE)
    if "s3" in requested_providers:
        _skip_if_none(s3_storage)
        storage_providers.append(s3_storage)

    if len(storage_providers) == len(cache_sizes):
        cache_sizes.pop()

    return get_cache_chain(storage_providers, cache_sizes)


@pytest.fixture(scope="session", autouse=True)
def clear_storages(memory_storage, local_storage, s3_storage):
    # executed before the first test

    print()
    print()

    if memory_storage:
        print("Clearing memory storage provider")
        memory_storage.clear()

    if local_storage:
        print("Clearing local storage provider")
        local_storage.clear()

    if s3_storage:
        print("Clearing s3 storage provider")
        s3_storage.clear()

    print()

    yield

    # executed after the last test
