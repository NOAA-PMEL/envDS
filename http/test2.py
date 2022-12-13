import asyncio
import signal
from aiohttp import web

class WebAPI():
    def __init__(self, address='localhost', port=8080) -> None:
        
        self.loop = asyncio.get_running_loop()
        
        self.loop.create_task(self.start_runner(address, port))

        self.doRun = True

    async def handle(self, request):
        name = request.match_info.get('name', "Anonymous")
        text = "Hello, " + name
        return web.Response(text=text)

    async def start_runner(self, address, port):
        app = web.Application()
        app.add_routes([web.get('/', self.handle),
                web.get('/{name}', self.handle)])
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, address, port)
        await site.start()

    async def shutdown(self):

        await self.runner.cleanup()
        self.doRun = False


# runners = []

# async def start_site(app, address='localhost', port=8080):
#     runner = web.AppRunner(app)
#     runners.append(runner)
#     await runner.setup()
#     site = web.TCPSite(runner, address, port)
#     await site.start()

# async def handle(request):
#     name = request.match_info.get('name', "Anonymous")
#     text = "Hello, " + name
#     return web.Response(text=text)

# loop = asyncio.get_event_loop()

# app = web.Application()
# app.add_routes([web.get('/', handle),
#                 web.get('/{name}', handle)])
# loop.create_task(start_site(app))

# app = web.Application()
# app.add_routes([web.get('/', handle),
#                 web.get('/{name}', handle)])
# loop.create_task(start_site(app, port=8083))

# app = web.Application()
# app.add_routes([web.get('/', handle),
#                 web.get('/{name}', handle)])
# loop.create_task(start_site(app, port=8082))

# # loop.create_task(start_site(web.Application()))
# # loop.create_task(start_site(web.Application(), port=8081))
# # loop.create_task(start_site(web.Application(), port=8082))

async def main():
    event_loop = asyncio.get_running_loop()

    api_list = []
    api_list.append(WebAPI(port=8080))
    api_list.append(WebAPI(port=8082))
    api_list.append(WebAPI(port=8083))

    def shutdown_handler(*args):
        for api in api_list:
            asyncio.create_task(api.shutdown())

    event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

    # do_run = True
    while any([api.doRun for api in api_list]):
        await asyncio.sleep(1)

    print("done")

if __name__ == "__main__":

    asyncio.run(main())

    # try:
    #     loop.run_forever()
    # except:
    #     pass
    # finally:
    #     for runner in runners:
    #         loop.run_until_complete(runner.cleanup())