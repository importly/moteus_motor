import asyncio
import os
import moteus
import sys
import json

address = os.getenv('ADDRESS', 'localhost')
port = int(os.getenv('PORT', 5135))

controllers = {
	1: moteus.Controller(id=1),
	2: moteus.Controller(id=2),
}

last_poses = {cid: None for cid in controllers}


async def handle_client(r, w):
	global last_poses
	client_add = w.get_extra_info('peername')
	print(f"Connected with {client_add}")

	try:
		data = await r.readuntil(b'\n\n')
		if not data.strip():
			print(f"No data from {client_add}")
			return
		commands = parse_commands(data.decode().strip())
		responses = []
		# print(f"Received commands from {client_add}: {commands}")
		for _, command in commands.items():
			cid = command.get("id")
			if cid in controllers:
				if command.get("d"):
					last_poses[cid] = command.get("p")
				state = await controllers[cid].query()

				responses.append({
					"id": cid,
					"ep": state.values[moteus.Register.POSITION],
					"v": state.values[moteus.Register.VELOCITY],
					"t": state.values[moteus.Register.TORQUE],
					"vo": state.values[moteus.Register.VOLTAGE],
					"te": state.values[moteus.Register.TEMPERATURE],
				})

		response = json.dumps(responses) + "\n\n"
		w.write(response.encode())
		# print(f"Sent response to {client_add}: {response}")
		await w.drain()
	except Exception as e:
		print(f"unexpected error from {client_add}: {e}")
	finally:
		w.close()
		print(f"connection closed with {client_add}")


def parse_commands(data):
	default_commands = {
		"id": None,
		"p": 0.0,
		"d": True,
		# add more stuff here if needed from client
	}

	commands = {}
	try:
		json_data = json.loads(data)
		for item in json_data:
			motor_id = item.get("id")
			if motor_id is not None:
				if motor_id not in commands:
					commands[motor_id] = {k: v for k, v in default_commands.items()}
				for key, value in item.items():
					if key in default_commands:
						if isinstance(default_commands[key], int):
							commands[motor_id][key] = int(value)
						elif isinstance(default_commands[key], float):
							commands[motor_id][key] = float(value)
						elif isinstance(default_commands[key], bool):
							commands[motor_id][key] = bool(value)
						else:
							commands[motor_id][key] = value
	except json.JSONDecodeError as error:
		print(f"JSON decode error: {error}")

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
