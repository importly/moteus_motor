import asyncio


async def send_position_command(position):
	reader, writer = await asyncio.open_connection('localhost', 5135)

	# Send position command
	writer.write(f"{position}\n".encode())

	# Read response
	response = await reader.readuntil(b'\n\n')
	print(response.decode())

	writer.close()
	await writer.wait_closed()


async def main():
	# Example positions to send
	positions = [0.0]

	for pos in positions:
		print(f"Sending position command: {pos}")
		await send_position_command(pos)
		print()


if __name__ == '__main__':
	asyncio.run(main())
