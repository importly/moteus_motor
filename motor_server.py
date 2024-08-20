import asyncio
import os
import moteus
import sys

address = os.getenv('ADDRESS', 'localhost')
port = int(os.getenv('PORT', 5135))

controllers = {
	1: moteus.Controller(id=1),
}

last_poses = {cid: None for cid in controllers}


async def handle_client(r, w):
	global last_poses
	client_add = w.get_extra_info('peername')
	print(f"Connected with {client_add}")

	try:
		data = await r.readuntil(b'\n')
		if not data.strip():
			print(f"No data from {client_add}")
			return
		print(parse_commands(data.decode().strip()))
		commands = parse_commands(data.decode().strip())
		responses = []
		for cid, position in commands.items():
			if cid in controllers:
				state = await controllers[cid].set_position(position=position, query=True)
				last_poses[cid] = position
				response = f"id={cid};ep={state.values[moteus.Register.POSITION]}\n"
				responses.append(response)

		response = ''.join(responses) + "\n"
		w.write(response.encode())
		await w.drain()
	except asyncio.IncompleteReadError:
		print(f"incomplete data from {client_add}. data: {data}")
	except ValueError as e:
		print(f"valueError from {client_add}: {e}")
		w.write(b"invalid command\n")
		await w.drain()
	except Exception as e:
		print(f"unexpected error from {client_add}: {e}")
	finally:
		w.close()
		print(f"connection closed with {client_add}")


def parse_commands(data):
	commands = {}
	parts = data.split(';')
	for part in parts:
		if '=' in part:
			key, value = part.split('=')
			if key == 'id':
				current_id = int(value)
			elif key == 'p':
				commands[current_id] = float(value)
	return commands


async def control_loop():
	global last_poses, controllers

	for controller in controllers.values():
		await controller.set_stop()

	while True:
		for cid, controller in controllers.items():
			if last_poses[cid] is not None:
				await controller.set_position(position=last_poses[cid], query=True)
		await asyncio.sleep(0.005)


async def main():
	control_task = asyncio.create_task(control_loop())
	print(f"Server started at {address}:{port}")
	server = await asyncio.start_server(handle_client, address, port)

	async with server:
		await server.serve_forever()

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