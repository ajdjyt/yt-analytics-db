<script>
    export let id
</script>

<section {id} class={"flex flex-col px-4 z-20"}>
    <div class="flex flex-col max-w-[85%] mx-auto w-full"> 
        <slot />
    </div>
</section>