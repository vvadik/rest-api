import json
from aiohttp import web


router = web.RouteTableDef()
temp_bd = {}


@router.get('/convert')
async def convert(request):
    data = await converter(request)
    return web.json_response(data)


@router.post('/database')
async def database(request: web.Request):
    data = await database_handler(request)
    return web.json_response(data)


async def database_handler(request: web.Request):
    merge = request.rel_url.query.get('merge')
    is_valid, reason = await check_data({'merge': merge})
    if not is_valid:
        return reason

    if int(merge) == 0:
        # drop table
        temp_bd = {}
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
        form_data['status'] = 200
        return form_data


async def converter(request):
    request_args = {
            'from': request.rel_url.query.get('from'),
            'to': request.rel_url.query.get('to'),
            'amount': request.rel_url.query.get('amount'),
        }

    is_valid, reason = await check_data(request_args)
    if not is_valid:
        return reason

    # do smth with data
    # data = {key: value for key, value in args.items()}
    
    request_args['status'] = 200
    return request_args


async def check_data(args):
    for key, value in args.items():
        if not value:
            return False, {
                'status': 400,
                'invalid argument': key,
            }
    return True, None


async def init_server():
    app = web.Application()
    app.add_routes(router)
    return app


if __name__ == "__main__":
    web.run_app(init_server(), port=8080)
