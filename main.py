import json
from aiohttp import web
from asyncio import Lock


router = web.RouteTableDef()
temp_db = {}
lock_db = Lock()


@router.get('/convert')
async def convert(request):
    data = await converter(request)
    return web.json_response(data)


@router.post('/database')
async def database(request: web.Request):
    data = await database_handler(request)
    return web.json_response(data)


async def database_handler(request: web.Request):


    global temp_db
    merge = request.rel_url.query.get('merge')
    is_valid, reason = await check_args({'merge': merge})
    if not is_valid:
        return reason

    if int(merge) == 0:
        # drop table
        temp_db = {}
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
        async with lock_db:
            for key, value in form_data.items():
                temp_db[key] = float(value) if key != 'MAIN' else value
        return {'status': 200}


async def converter(request):


    global temp_db

    print(temp_db)

    request_args = {
            'from': request.rel_url.query.get('from'),
            'to': request.rel_url.query.get('to'),
            'amount': request.rel_url.query.get('amount'),
        }

    is_valid, reason = await check_args(request_args)
    if not is_valid:
        return reason

    is_valid, reason = await check_keys_db(request_args)
    if not is_valid:
        return reason

    request_args['amount'] = float(request_args['amount'])

    if request_args['from'] == temp_db['MAIN']:
        amount = request_args['amount'] * temp_db[request_args['to']]
    elif request_args['to'] == temp_db['MAIN']:
        amount = request_args['amount'] / temp_db[request_args['from']]
    else:
        amount_main = request_args['amount'] / temp_db[request_args['from']]
        amount = amount_main * temp_db[request_args['to']]
    return {'status': 200, 'amount': amount}


async def check_args(args):
    for key, value in args.items():
        if not value:
            return False, {
                'status': 400,
                'invalid argument': key,
            }
    return True, None


async def check_keys_db(request_args):


    global temp_db

    if not ((request_args['from'] in temp_db
            or request_args['from'] == temp_db['MAIN'])
            and (request_args['to'] in temp_db
                 or request_args['to'] == temp_db['MAIN'])):
        return False, {
            'status': 400,
            'reason': 'key not found'
        }
    return True, None


async def init_server():
    app = web.Application()
    app.add_routes(router)
    return app


if __name__ == "__main__":
    web.run_app(init_server(), port=8080)
