import json
import aioredis
from aiohttp import web


router = web.RouteTableDef()
temp_db = {}


@router.get('/convert')
async def convert(request: web.Request) -> web.Response:
    data = await converter(request)
    return web.json_response(data)


@router.post('/database')
async def database(request: web.Request) -> web.Response:
    data = await database_handler(request)
    return web.json_response(data)


async def database_handler(request: web.Request) -> dict:


    global temp_db
    redis = request.app['redis']
    merge = request.rel_url.query.get('merge')
    is_valid, reason = await check_args({'merge': merge})
    if not is_valid:
        return reason

    if merge == '0':
        # drop table
        temp_db = {}
        # await redis.mset({'a': 1, 'asd': 'aaa'})

        # data = await redis.mget('a')
        # print('mget one', data)

        # print('mget two', await redis.mget('a', 'asd'))
        await redis.flushdb()
        # print('mget two', await redis.mget('a', 'asd'))


        return {'status': 200}
    else:
        try:
            form_data = await request.json()
        except json.decoder.JSONDecodeError as error:
            return {
                'status': 400,
                'reason': 'malformed body content',
                'exception': str(error)
            }

        is_valid, reason, form_data = await convert_updating_keys(form_data)  # в бд всегда хранится строка, ее придется кастовать когда достаю
        if not is_valid:
            return reason

        for key, value in form_data.items():
            temp_db[key] = value

        await redis.mset(form_data)

        return {'status': 200}


async def converter(request: web.Request) -> dict:


    global temp_db
    redis = request.app['redis']


    request_args = {
            'from': request.rel_url.query.get('from'),
            'to': request.rel_url.query.get('to'),
            'amount': request.rel_url.query.get('amount'),
        }

    is_valid, reason = await check_args(request_args)
    if not is_valid:
        return reason

    is_valid, reason = await check_keys_in_db(request_args, redis)
    if not is_valid:
        return reason

    amount_request = float(request_args['amount'])

    key_from, key_to, key_main = await redis.mget(request_args['from'], 
                                                  request_args['to'],
                                                  'MAIN')
    key_from, key_to = float(key_from), float(key_to)

    if request_args['from'] == key_main:
        amount = amount_request * temp_db[request_args['to']]
    elif request_args['to'] == key_main:
        amount = amount_request / key_from
    else:
        amount_main = amount_request / key_from
        amount = amount_main * key_to
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

    keys = await redis.mget(request_args['from'], request_args['to'], 'MAIN')
    for key in keys:
        if key is None:
            return (False,
                    {'status': 400,
                     'reason': 'key not found'})
    return True, {}

    print(keys)

    if ((keys[0] is None
         or request_args['from'] != keys[2])
            and (keys[1] is None
                 or request_args['to'] != keys[2])):
        return (False,
                {'status': 400,
                 'reason': 'key not found'})
    return True, {}



    # global temp_db
    #
    # if not ((request_args['from'] in temp_db
    #         or request_args['from'] == temp_db['MAIN'])
    #         and (request_args['to'] in temp_db
    #              or request_args['to'] == temp_db['MAIN'])):
    #     return (False,
    #             {'status': 400,
    #              'reason': 'key not found'})
    # return True, {}


async def convert_updating_keys(request_args: dict) -> (bool, dict, dict):
    for key, value in request_args.items():
        if key != 'MAIN':
            try:
                request_args[key] = float(value)
            except ValueError:
                return (False,
                        {'status': 400,
                         'reason': f'Wrong format value {value}. '
                                   f'Expected int or double'},
                        {})

    return True, {}, request_args


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
    # data = r.mset({"Croatia": "Zagreb", "Bahamas": "Nassau"})
    # print(data)
    # print(r.get("Bahamas"))
    web.run_app(init_server(), port=8080)
