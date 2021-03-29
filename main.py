import json
import aioredis
from aiohttp import web


router = web.RouteTableDef()


@router.get('/convert')
async def convert(request: web.Request) -> web.Response:
    data = await converter(request)
    return web.json_response(data)


@router.post('/database')
async def database(request: web.Request) -> web.Response:
    data = await database_handler(request)
    return web.json_response(data)


async def database_handler(request: web.Request) -> dict:
    redis = request.app['redis']
    merge = request.rel_url.query.get('merge')
    valid, reason = await check_args({'merge': merge})
    if not valid:
        return reason

    if merge == '0':
        await redis.flushdb()
        return {'status': 200}
    elif merge == '1':
        try:
            form_data = await request.json()
        except json.decoder.JSONDecodeError as error:
            return {
                'status': 400,
                'reason': 'malformed body content',
                'exception': str(error)
            }

        valid, reason = await check_updating_keys(form_data)
        if not valid:
            return reason

        await redis.mset(form_data)
        return {'status': 200}


async def converter(request: web.Request) -> dict:
    redis = request.app['redis']
    request_args = {
            'from': request.rel_url.query.get('from'),
            'to': request.rel_url.query.get('to'),
            'amount': request.rel_url.query.get('amount'),
        }

    valid, reason = await check_args(request_args)
    if not valid:
        return reason

    # TODO: делать exists а не mget
    valid, reason = await check_keys_in_db(request_args, redis)
    if not valid:
        return reason

    (key_from_amount,
     key_to_amount,
     key_main) = await redis.mget(request_args['from'],
                                  request_args['to'],
                                  'MAIN')
    key_from_amount, key_to_amount = float(key_from_amount), float(key_to_amount)
    amount_request = float(request_args['amount'])

    if request_args['from'] == key_main:
        amount = amount_request * key_to_amount
    elif request_args['to'] == key_main:
        amount = amount_request / key_from_amount
    else:
        amount_main = amount_request / key_from_amount
        amount = amount_main * key_to_amount
    return {'status': 200, 'amount': amount}


async def check_args(args: dict) -> (bool, dict):
    for key, value in args.items():
        if not value:
            return (False,
                    {'status': 400,
                     'invalid argument': key})
    return True, {}


async def check_keys_in_db(request_args: dict,
                           redis: aioredis.commands.Redis) -> (bool, dict):
    # TODO: надо ипользовать exists,
    # если только не придет False и придется граничить если захотим сделать 0
    keys = await redis.mget(request_args['from'], request_args['to'], 'MAIN')
    for key in keys:
        if key is None:
            return (False,
                    {'status': 400,
                     'reason': 'key not found'})
    return True, {}


async def check_updating_keys(request_args: dict) -> (bool, dict):
    for key, value in request_args.items():
        if key != 'MAIN':
            try:
                float(value)
            except ValueError:
                return (False,
                        {'status': 400,
                         'reason': f'Wrong format value {value}. '
                                   f'Expected int or double'})

    return True, {}


async def close_redis(app):
    app['redis'].close()


async def init_server() -> web.Application:
    app = web.Application()
    app.add_routes(router)

    app['redis'] = await aioredis.create_redis(('redis', 6379),
                                               encoding='UTF-8',
                                               db=1)
    app.on_shutdown.append(close_redis)
    return app


if __name__ == "__main__":
    web.run_app(init_server(), port=8080)
