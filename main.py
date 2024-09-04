import asyncio
import os
import sys
import time
import server  # Import the compiled Cython module


async def main():
	control_task = asyncio.create_task(server.control_loop())
	print(f"Server started at {server.address}:{server.port}")
	server_inst = await asyncio.start_server(server.handle_client, server.address, server.port)

	async with server_inst:
		await server_inst.serve_forever()

	control_task.cancel()
	await control_task


if __name__ == '__main__':
	while True:
		try:
			print("Starting server...")
			asyncio.run(main())
		except Exception as e:
			print(f"Server crashed with error: {e}")
			print("Restarting server...")
			os.execv(sys.executable, ['python'] + sys.argv)
