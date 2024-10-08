<script>
	import SectionWrapper from "./SectionWrapper.svelte";
</script>

<SectionWrapper id="Hero">
    <div class="min-h-screen flex flex-row ">
        <div class="flex flex-col w-1/2 items-center justify-center place-items-center ">
            <p class="text-white " style="font-family: Anton"> Get analytics for your <span class="text-gray-500">Channel</span></p>
            <i class="fa-brands fa-youtube text-[15em] text-indigo-400"></i>
        </div>
        <div class="flex flex-col w-1/2 justify-center place-items-center">
            <div class="mb-6">
                <label for="Start" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white">Get started</label>
                <input type="text" id="Start" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500">
            </div>
        </div>
    </div>
</SectionWrapper>