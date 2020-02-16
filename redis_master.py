import redis
import sys
import tabulate


def get_redis_key_value(
    redis_client,
    key,
):
    try:
        return redis_client.llen(key)
    except redis.exceptions.ResponseError:
        return int(redis_client.get(key))


def main():
    port_map = {'prod': 54379, 'dev': 34379}
    env = sys.argv[1]

    try:
        port = port_map[env]
    except Exception:
        print(f'<{env}> prod/dev')

        return

    redis_client = redis.Redis(host='localhost', port=port)
    keys = redis_client.keys()
    results = {}

    for queue in keys:
        if '_allowed' not in str(queue):
            results[queue] = get_redis_key_value(redis_client, queue)

    queues = (
        (
            key,
            results[key],
        )
        for key in sorted(results.keys())
        if 'quota_' not in str(key)
    )

    quota_queues = (
        (
            key,
            results[key],
        )
        for key in sorted(results.keys())
        if 'quota_' in str(key)
    )

    print(
        tabulate.tabulate(
            tabular_data=queues,
            headers=(f'{env} - queue', 'size'),
            tablefmt='fancy_grid',
        )
    )

    print(
        tabulate.tabulate(
            tabular_data=quota_queues,
            headers=(f'{env} - service', 'quota'),
            tablefmt='fancy_grid',
        )
    )


if __name__ == '__main__':
    main()
