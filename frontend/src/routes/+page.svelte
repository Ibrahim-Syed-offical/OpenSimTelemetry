<script lang="ts">
  import AppSidebar from "$lib/components/app-sidebar.svelte";
  import * as Breadcrumb from "$lib/components/ui/breadcrumb/index";
  import { Separator } from "$lib/components/ui/separator/index";
  import * as Sidebar from "$lib/components/ui/sidebar/index";
  import * as Menubar from "$lib/components/ui/menubar/index";
  import * as Tabs from "$lib/components/ui/tabs/index";
  import * as Card from "$lib/components/ui/card/index";
  import { onMount } from 'svelte';
  import { AspectRatio } from "$lib/components/ui/aspect-ratio/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  
  import * as Chart from "$lib/components/ui/chart/index.js";
  import { scaleUtc } from "d3-scale";
  import { curveLinear } from "d3-shape";
  import { Area, AreaChart, LinearGradient } from "layerchart";
  import TrendingUpIcon from "@lucide/svelte/icons/trending-up";
  import { scaleLinear } from "d3-scale";

  // --- UI State ---
  let bookmarks = $state(false); 
  let fullUrls = $state(true);
  let profileRadioValue = $state("benoit");
  let currentSector = $state<number>(1);
  

 
  let lapTimes = $state<any[]>([]);
  let selectedLap = $state<any>(null);
  let liveMode = $state(false);
  let isPlaying = $state(false); // Added missing variable
  let playbackDistance = $state(0); // Added missing variable

  interface TelemetryState {
      gas: number[];
      brake: number[];
      steering: number[];
      normalized_pos: number[];
      lapTime: string;
      trackName: string;
      car: string;
  }

  let telemetryData = $state<TelemetryState>({
    gas: [],
    brake: [],
    steering: [],
    normalized_pos: [],
    lapTime: '0:00.000',
    trackName: 'Waiting for data...',
    car: 'Select a lap',
  });

  let currentTrace = $state({gas: [], brake: [], steer: [], normPos: [] });

  let gasChartData = $derived.by(() => {
  if (!currentTrace.gas.length) return [];
  
  const MAX_POINTS = 300; // Hard cap for visual performance
  const step = Math.max(1, Math.floor(currentTrace.gas.length / MAX_POINTS));
  const result = [];
  
  for (let i = 0; i < currentTrace.gas.length; i += step) {
    result.push({
      distance: currentTrace.normPos[i],
      gas: currentTrace.gas[i] * 100,
      brake: currentTrace.brake[i] * 100
    });
  }
  return result;
});
  const chartConfig = {
    gas: { label: "Throttle", color: "var(--color-emerald-500)" },
    brake: { label: "Brake", color: "var(--color-red-500)" }
  } satisfies Chart.ChartConfig;

  onMount(() => {
    const loadLaps = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8055/laps');
        const data = await res.json();
        lapTimes = data.map((d: any, i: number) => ({
          uuid: d.uuid,
          lap: data.length - i,
          time: d.lap_time,
          car: d.car,
          track: d.track,
        }));
      } catch (e) {
        console.error("Error fetching laps", e);
      }
    };
    loadLaps();
  });

  async function selectLap(lap: any) {
    selectedLap = lap;
    liveMode = false;
    telemetryData.car = lap.car;
    telemetryData.trackName = lap.track;

    try {
      const res = await fetch(`http://127.0.0.1:8055/laps/${lap.uuid}/telemetry`);
      const fetchedData = await res.json();
      
      currentTrace = {
        gas: fetchedData.gas ?? [],
        brake: fetchedData.brake ?? [],
        steer: fetchedData.steering ?? [],
        normPos: fetchedData.normalized_pos || []
      };

      telemetryData = { ...telemetryData, ...currentTrace };
      
      if (currentTrace.normPos.length > 0) isPlaying = true;
    } catch (e) {
      console.error("Failed to load telemetry", e);
    }
  }
</script>

<Sidebar.Provider>
  <AppSidebar {lapTimes} onSelectLap={selectLap} />
  
  <Sidebar.Inset class="flex flex-col h-screen overflow-hidden bg-background">
    <header class="flex h-14 shrink-0 items-center justify-between gap-2 border-b px-4">
      <div class="flex items-center gap-2">
        <Sidebar.Trigger />
        <Separator orientation="vertical" class="mr-2 h-4" />
        <Breadcrumb.Root>
          <Breadcrumb.List>
            <Breadcrumb.Item>
              <Breadcrumb.Link href="/">Dashboard</Breadcrumb.Link>
            </Breadcrumb.Item>
            <Breadcrumb.Separator />
            <Breadcrumb.Item>
              <Breadcrumb.Page>{telemetryData.trackName}</Breadcrumb.Page>
            </Breadcrumb.Item>
          </Breadcrumb.List>
        </Breadcrumb.Root>
      </div>

      <Menubar.Root class="border-none shadow-none">
        <Menubar.Menu>
          <Menubar.Trigger>File</Menubar.Trigger>
          <Menubar.Content>
            <Menubar.Item>Export Telemetry</Menubar.Item>
            <Menubar.Item>Settings</Menubar.Item>
          </Menubar.Content>
        </Menubar.Menu>
        <Menubar.Menu>
          <Menubar.Trigger>View</Menubar.Trigger>
          <Menubar.Content>
            <Menubar.CheckboxItem bind:checked={bookmarks}>Show Bookmarks</Menubar.CheckboxItem>
            <Menubar.CheckboxItem bind:checked={fullUrls}>Full URLs</Menubar.CheckboxItem>
          </Menubar.Content>
        </Menubar.Menu>
      </Menubar.Root>
    </header>

    <div class="flex flex-1 overflow-hidden">
  
  <main class="flex flex-1 flex-col p-4 overflow-y-auto bg-muted/20">
    <div class="w-full max-w-7xl mx-auto">
      <Card.Root class="overflow-hidden border-muted/50 shadow-lg">
        <Card.Content class="p-0">
          <AspectRatio ratio={16 / 9} class="bg-black">
          <div class="absolute top-4 left-4 flex gap-2">
            <Badge variant="outline" class="bg-black/50 backdrop-blur-md border-emerald-500/50 text-emerald-500">
              Sector {currentSector}
            </Badge>
            <Badge variant="secondary" class="bg-black/50 backdrop-blur-md">
              {telemetryData.trackName}
            </Badge>
          </div>
            </AspectRatio>
        </Card.Content>
      </Card.Root>
    </div>
  </main>

 <aside class="w-[380px] shrink-0 border-l bg-background hidden xl:flex flex-col">
  <Tabs.Root value="traces" class="flex flex-col h-full">
    <div class="p-4 border-b">
      <Tabs.List class="grid w-full grid-cols-2">
        <Tabs.Trigger value="traces">Traces</Tabs.Trigger>
        <Tabs.Trigger value="setup">Setup</Tabs.Trigger>
      </Tabs.List>
    </div>
    
    <Tabs.Content value="traces" class="flex-1 overflow-y-auto p-4">
      <div class="flex flex-col gap-4">
        <p class="text-xs font-bold uppercase text-muted-foreground tracking-tight">Telemetry Traces</p>
        
                <Card.Root>
          <Card.Header>
            <Card.Title>Brake/Throttle</Card.Title>
          </Card.Header>
            <Card.Content>
              <Chart.Container config={chartConfig}>
                <AreaChart
                  data={gasChartData}
                  x="distance"
                  xScale={scaleLinear()} 
                  yPadding={[0, 1]}
                  series={[
                    {
                      key: "gas",
                      label: "Throttle",
                      color: "#10b981", // Emerald
                    },
                    {
                      key: "brake",
                      label: "Brake",
                      color: "#ef4444", // Red
                    },
                  ]}
                  seriesLayout="overlap"
                  props={{
                    xAxis: {
                      ticks: 5,
                      
                      
                    },
                    yAxis: { 
                      format: (v: number) => `${(v * 100).toFixed(0)}%` 
                    },
                  }}
                >
                  {#snippet tooltip()}
                    <Chart.Tooltip
                      indicator="dot"
                      labelFormatter={(v: number) => `Track Pos: ${(v * 100).toFixed(1)}%`}
                    />
                  {/snippet}

                  {#snippet marks({ context })}
                    {#each context.series.visibleSeries as s (s.key)}
                      <LinearGradient
                        stops={[
                          s.color ?? "",
                          "color-mix(in lch, " + s.color + " 10%, transparent)",
                        ]}
                        vertical
                      >
                        {#snippet children({ gradient })}
                          <Area
                            seriesKey={s.key}
                            curve={curveLinear}
                            fillOpacity={0.3}
                            line={{ class: "stroke-2" }}
                            motion="tween"
                            {...s.props}
                            fill={gradient}
                          />
                        {/snippet}
                      </LinearGradient>
                    {/each}
                  {/snippet}
                </AreaChart>
              </Chart.Container>
            </Card.Content>
          <Card.Footer>
            <div class="flex w-full items-start gap-2 text-sm">
              <div class="grid gap-2">
              </div>
            </div>
          </Card.Footer>
        </Card.Root>
        
        <div class="h-32 rounded-xl border bg-muted/30 border-dashed flex items-center  justify-center text-muted-foreground text-[10px] uppercase">
            Steering
        </div>

        {#if !selectedLap}
          <div class="py-10 border-t mt-4">
            <p class="text-sm text-muted-foreground italic text-center">Select a lap for live data</p>
          </div>
        {/if}
      </div>
    </Tabs.Content>
  </Tabs.Root>
</aside>
</div>

</Sidebar.Inset>
</Sidebar.Provider>