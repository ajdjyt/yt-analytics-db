<script lang="ts">
	import { onMount } from 'svelte';
	import axios from 'axios';

	let channelName = '';
	let channelData: any = null;
	let error = '';

	const fetchChannelData = async () => {
		try {
			const response = await axios.post('http://localhost:5000/api/channels', {
				channelName: channelName
			});
			channelData = response.data;
			error = '';
		} catch (err) {
			error = err.response?.data?.error || 'Something went wrong.';
		}
	};
</script>

<main class="p-6">
	<h1 class="text-3xl font-bold mb-4">YouTube Channel Analyzer</h1>

	<div class="mb-4">
		<input
			bind:value={channelName}
			type="text"
			placeholder="Enter channel name"
			class="p-2 border border-gray-300 rounded"
		/>
		<button on:click={fetchChannelData} class="ml-2 p-2 bg-blue-500 text-white rounded">
			Get Channel Data
		</button>
	</div>

	{#if error}
		<p class="text-red-500">{error}</p>
	{/if}

	{#if channelData}
		<div class="mt-4">
			<h2 class="text-xl font-bold">{channelData.name}</h2>
			<p>Channel added successfully!</p>
		</div>
	{/if}
</main>
