<script lang="ts">
	import { addChannel, deleteChannel } from '../lib/api';
	let channelId: string = '';

	async function handleAddChannel() {
		const response = await addChannel(channelId);
		alert(`Channel ${response.name} added!`);
	}

	async function handleDeleteChannel() {
		await deleteChannel(channelId);
		alert('Channel deleted!');
	}
</script>

<div class="p-4 max-w-md mx-auto">
	<h1 class="text-2xl font-bold mb-4">YouTube Channel Management</h1>
	<input
		type="text"
		bind:value={channelId}
		placeholder="Enter YouTube Channel ID"
		class="border border-gray-300 rounded p-2 mb-2 w-full"
	/>
	<div class="flex space-x-2">
		<button on:click={handleAddChannel} class="bg-blue-500 text-white rounded px-4 py-2"
			>Add Channel</button
		>
		<button on:click={handleDeleteChannel} class="bg-red-500 text-white rounded px-4 py-2"
			>Delete Channel</button
		>
	</div>
</div>
