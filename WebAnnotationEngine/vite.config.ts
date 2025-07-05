import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig({
	plugins: [sveltekit()],

	test: {
		include: ['src/**/*.{test,spec}.{js,ts}']
	},
	server: {
		host: true, // or your specific IP
		allowedHosts: [
		'annotation.utokyo-jsl.org',
		'annotation2.utokyo-jsl.org'
		]
  }	
});
