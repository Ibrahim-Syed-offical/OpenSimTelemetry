<script lang="ts">
    import NavMain from "./nav-main.svelte";
    import SidebarOptInForm from "./sidebar-opt-in-form.svelte";
    import * as Sidebar from "$lib/components/ui/sidebar/index.js";
    import GalleryVerticalEndIcon from "@lucide/svelte/icons/gallery-vertical-end";
    import type { ComponentProps } from "svelte";

    // 1. Define the props to accept lapTimes and the selection function
    let { 
        ref = $bindable(null), 
        lapTimes = [], 
        onSelectLap,
        ...restProps 
    }: ComponentProps<typeof Sidebar.Root> & { 
        lapTimes: any[], 
        onSelectLap?: (lap: any) => void 
    } = $props();

    // 2. Transform your database laps into the format NavMain expects
    // We use $derived so this updates automatically whenever lapTimes changes
    let navItems = $derived([
        {
            title: "Session Laps",
            url: "#",
            items: lapTimes.map(lap => ({
                title: `L${lap.lap} - ${lap.time}`,
                url: "#",
                // We'll handle the click via a custom dispatcher or raw items
                isActive: false,
                uuid: lap.uuid,
                raw: lap
            }))
        }
    ]);
</script>

<Sidebar.Root bind:ref {...restProps}>
    <Sidebar.Header>
        <Sidebar.Menu>
            <Sidebar.MenuItem>
                <Sidebar.MenuButton size="lg">
                    {#snippet child({ props })}
                        <a href="##" {...props}>
                            <div class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                                <GalleryVerticalEndIcon class="size-4" />
                            </div>
                            <div class="flex flex-col gap-0.5 leading-none">
                                <span class="font-medium">OpenSimTelemetry</span>
                                <span class="text-xs opacity-70">v1.0.0</span>
                            </div>
                        </a>
                    {/snippet}
                </Sidebar.MenuButton>
            </Sidebar.MenuItem>
        </Sidebar.Menu>
    </Sidebar.Header>

    <Sidebar.Content>
        <Sidebar.Group>
            <Sidebar.GroupLabel>Database Laps</Sidebar.GroupLabel>
            <Sidebar.Menu>
                {#each lapTimes as lap}
                    <Sidebar.MenuItem>
                        <Sidebar.MenuButton onclick={() => onSelectLap?.(lap)}>
                            <div class="flex flex-col items-start overflow-hidden">
                                <span class="truncate font-medium text-sm">Lap {lap.lap}</span>
                                <span class="truncate text-xs text-muted-foreground font-mono">{lap.time}</span>
                            </div>
                        </Sidebar.MenuButton>
                    </Sidebar.MenuItem>
                {/each}
            </Sidebar.Menu>
        </Sidebar.Group>
    </Sidebar.Content>

    <Sidebar.Footer>
        <div class="p-1">
            <SidebarOptInForm />
        </div>
    </Sidebar.Footer>
    <Sidebar.Rail />
</Sidebar.Root>