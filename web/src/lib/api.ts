const BASE_URL = 'http://localhost:5000/api';

export interface Channel {
	channelId: string;
	name: string;
}

export async function addChannel(channelId: string): Promise<Channel> {
	const response = await fetch(`${BASE_URL}/channels`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ channelId })
	});
	return response.json();
}

export async function deleteChannel(channelId: string): Promise<void> {
	await fetch(`${BASE_URL}/channels/${channelId}`, {
		method: 'DELETE'
	});
}

export interface ChannelStats {
	median_viewership: number;
	frequency: number;
}

export async function fetchChannelStats(channelId: string): Promise<ChannelStats> {
	const response = await fetch(`${BASE_URL}/channels/${channelId}/stats`);
	return response.json();
}
