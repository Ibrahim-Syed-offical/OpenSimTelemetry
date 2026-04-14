<script lang="ts">
  import { onMount } from 'svelte';
  import TrackMap from '$lib/TrackMap.svelte';
  import TelemetryGraph from '$lib/TelemetryGraph.svelte';

  // --- UI STATE ---
  let selectedLap = $state<any>(null);
  let liveMode    = $state(false);
  interface TelemetryState {
      // Array data coming from the .h5 files
      gas: number[];
      brake: number[];
      steering: number[];
      normalized_pos: number[];
      
      // Metadata coming from the SQLite database
      lapTime: string;
      sector1: string | null;
      sector2: string | null;
      trackName: string;
      car: string;
  }
  let telemetryData = $state<TelemetryState>({
    gas: [],
    brake: [],
    steering: [],
    normalized_pos: [],
    lapTime: '0:00.000',
    sector1: null,
    sector2: null,
    trackName: 'Waiting for data...',
    car: 'Select a lap',
});
  
  let carCoords = $state({ x: 0.5, y: 0.5 });
  let lapTimes = $state<any[]>([]);

  // --- PLAYBACK STATE ---
  let isPlaying = $state(false);
  let playbackDistance = $state(0); 
  let playbackSpeed = 0.001; 
  
  // Initialize current playback time for the UI display
  let playbackTime = $state(0);

  let currentTrace = $state({gas: [], brake: [], steer: [], normPos: [] });

  // Define rafId outside so it's accessible to onMount cleanup
  let rafId: number;
  let lastFrameTime = performance.now();

  function playbackLoop(now: number) {
    if (isPlaying && !liveMode) {
      playbackDistance += playbackSpeed;
      if (playbackDistance >= 1) {
        playbackDistance = 0;
        isPlaying = false;
      }
    }
    updateDashboardFromDistance();
    rafId = requestAnimationFrame(playbackLoop);
  }

  function updateDashboardFromDistance() {
    if (!currentTrace.normPos || currentTrace.normPos.length === 0) return;

    // Use findIndex to find the position on the track spline
    let index = currentTrace.normPos.findIndex(p => p >= playbackDistance);
    if (index === -1) index = currentTrace.normPos.length - 1;

    // Update the UI playback time based on the data index
    playbackTime = currentTrace.normPos[index] || 0;

    telemetryData = {
      ...telemetryData,
      gas: [Math.round(currentTrace.gas[index] * 100)],
      brake: [Math.round(currentTrace.brake[index] * 100)],
      steering: [Math.round(currentTrace.steer[index] * 180)],
    };
  }

  onMount(() => {
    rafId = requestAnimationFrame(playbackLoop);
    
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
          valid: true,
          best: false, 
          s1: '--', s2: '--', s3: '--'
        }));
      } catch (e) {
        console.error("Error fetching laps from Python", e);
      }
    };

    loadLaps();

    // Properly cancel the animation frame on component destruction 
    return () => cancelAnimationFrame(rafId);
  });

  async function selectLap(lap: any) {
    selectedLap = lap;
    liveMode = false;
    isPlaying = false;
    playbackDistance = 0;
    
    telemetryData.car = lap.car;
    telemetryData.trackName = lap.track;

    try {
      const [telemetryRes] = await Promise.all([
        fetch(`http://127.0.0.1:8055/laps/${lap.uuid}/telemetry`),
      ]);

      const fetchedData = await telemetryRes.json();
      
      currentTrace = {
        gas: fetchedData.gas ?? [],
        brake: fetchedData.brake ?? [],
        steer: fetchedData.steering ?? [],
        normPos: fetchedData.normalized_pos || []
      };
      
      telemetryData.gas = fetchedData.gas ?? [];
      telemetryData.brake = fetchedData.brake ?? [];
      telemetryData.steering = fetchedData.steering ?? [];
      telemetryData.normalized_pos = fetchedData.normalized_pos ?? [];
    } catch (e) {
      console.error("Failed to load telemetry from Python", e);
    }

      if (currentTrace.normPos.length > 0) {
        isPlaying = true; 
      }
    }
  function formatTime(seconds: number) {
    if (!seconds || isNaN(seconds)) return "0:00.000";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${m}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }
</script>

<div class="shell">
  <header class="topbar">
    <div class="topbar-left">
      <div class="logo">
        <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="14" r="13" stroke="#10b981" stroke-width="2"/>
          <path d="M8 14 L13 9 L20 14 L13 19 Z" fill="#10b981"/>
        </svg>
        <span class="brand">DeltaTelemetry</span>
      </div>
      <div class="session-pill" class:live={liveMode}>
        <span class="session-dot"></span>
        <span class="session-type">{liveMode ? 'LIVE' : 'PLAYBACK'}</span>
      </div>
    </div>

    <div class="topbar-center">
        <span class="track-car-name">{telemetryData.trackName}</span>
        <span class="track-divider">•</span>
        <span class="track-car-sub">{telemetryData.car}</span>
    </div>

    <div class="topbar-right">
      <div class="meta-chip">
        <span class="meta-icon">⏱</span>
        <span class="meta-label">{formatTime(playbackTime)}</span>
      </div>
    </div>
  </header>

  <main class="dashboard">
    <aside class="panel left-panel">
      <div class="panel-header">
        <h2 class="panel-title">Session Laps</h2>
        <button class="go-live-btn" class:active={liveMode} onclick={() => liveMode = true}>
          <span class="gli-dot"></span> LIVE
        </button>
      </div>
      <div class="laps-list">
        {#each lapTimes as lap}
          <button
            class="lap-row"
            class:best={lap.best}
            class:selected={selectedLap?.uuid === lap.uuid}
            onclick={() => selectLap(lap)}
          >
            <div class="lap-row-top">
              <span class="lap-num">L{lap.lap}</span>
              <span class="lap-time">{lap.time}</span>
            </div>
          </button>
        {/each}
      </div>
    </aside>

    <section class="panel center-panel">
      <div class="map-container">
        <TrackMap {playbackDistance} normPosArray={currentTrace.normPos} trackName={telemetryData.trackName ?? ''} />
      </div>
    </section>

    <aside class="panel right-panel">
        <div class="panel-header">
            <h2 class="panel-title">Trace Data</h2>
        </div>
        <div class="graphs-stack">
            <TelemetryGraph label="THROTTLE" unit="%" color="#10b981" value={telemetryData.gas ?? 0} max={100} />
            <TelemetryGraph label="BRAKE"    unit="%" color="#ef4444" value={telemetryData.brake    ?? 0} max={100} />
            <TelemetryGraph label="STEER"    unit="°" color="#c084fc" value={telemetryData.steering   ?? 0} max={180} />
        </div>
    </aside>
  </main>

  {#if !liveMode}
    <footer class="playback-footer">
  <div class="scrubber-container">
    <span class="time-readout">DIST</span>
    <input 
      class="scrubber" 
      min="0" 
      max="1" 
      step="0.001" 
      bind:value={playbackDistance}
    />
    <span class="time-readout">{(playbackDistance * 100).toFixed(1)}%</span>
  </div>
</footer>
  {/if}
</div>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
  
  :global(*) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) {
    background: #0f172a; color: #f8fafc;
    font-family: 'Inter', sans-serif; overflow: hidden;
  }

  .shell { display: flex; flex-direction: column; height: 100vh; width: 100vw; }

  /* TOPBAR */
  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    height: 56px; padding: 0 20px; background: #1e293b; border-bottom: 1px solid #334155; flex-shrink: 0;
  }
  .topbar-left { display: flex; align-items: center; gap: 16px; }
  .logo { display: flex; align-items: center; gap: 8px; }
  .brand { font-size: 1rem; font-weight: 600; color: #f8fafc; letter-spacing: -0.2px; }

  .session-pill {
    display: flex; align-items: center; gap: 6px;
    background: #0f172a; border: 1px solid #334155;
    padding: 4px 12px; border-radius: 6px;
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.5px;
  }
  .session-pill.live .session-dot { background: #10b981; animation: pulse 2s infinite; }
  .session-pill:not(.live) .session-dot { background: #38bdf8; }
  .session-dot { width: 6px; height: 6px; border-radius: 50%; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  .session-type { color: #94a3b8; }

  .topbar-center { display: flex; align-items: center; gap: 8px; }
  .track-car-name { font-size: 0.85rem; font-weight: 600; color: #e2e8f0; }
  .track-divider { color: #64748b; font-size: 0.8rem; }
  .track-car-sub  { font-size: 0.8rem; color: #94a3b8; font-weight: 500; }

  .topbar-right { display: flex; align-items: center; gap: 12px; }
  .meta-chip {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 10px; border-radius: 6px;
    background: #0f172a; border: 1px solid #334155;
    font-size: 0.75rem; color: #cbd5e1;
  }
  .meta-label { font-family: 'JetBrains Mono', monospace; font-weight: 500; }

  /* DASHBOARD GRID */
  .dashboard {
    display: grid; grid-template-columns: 300px 1fr 340px; gap: 16px;
    padding: 16px; flex: 1; overflow: hidden;
  }

  .panel {
    background: #1e293b; border: 1px solid #334155; border-radius: 10px;
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .panel-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 16px; border-bottom: 1px solid #334155; background: #1e293b; flex-shrink: 0;
  }
  .panel-title { font-size: 0.8rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }

  /* LEFT PANEL - LAPS */
  .go-live-btn {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 10px; border-radius: 4px;
    background: transparent; border: 1px solid #334155;
    font-family: 'Inter', sans-serif; font-size: 0.7rem; font-weight: 600;
    color: #94a3b8; cursor: pointer; transition: all 0.2s;
  }
  .go-live-btn.active { background: #064e3b; border-color: #059669; color: #34d399; }
  .gli-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

  .laps-list { flex: 1; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 6px; }
  .lap-row {
    background: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 10px 12px;
    cursor: pointer; text-align: left; width: 100%; transition: all 0.15s;
    border-left: 3px solid transparent;
  }
  .lap-row:hover { border-color: #334155; }
  .lap-row.selected { background: #1e293b; border-color: #475569; border-left-color: #38bdf8; }
  .lap-row.best { border-left-color: #a855f7; }
  .lap-row-top { display: flex; justify-content: space-between; align-items: center; }
  .lap-num { font-size: 0.7rem; font-weight: 600; color: #64748b; }
  .lap-time { font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 600; color: #e2e8f0; }

  /* CENTER PANEL - MAP */
  .center-panel { background: #0f172a; }
  .map-container { flex: 1; min-height: 0; padding: 10px; display: flex; align-items: center; justify-content: center;}

  /* RIGHT PANEL - GRAPHS */
  .graphs-stack { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

  /* PLAYBACK FOOTER */
  .playback-footer {
    display: flex; align-items: center; gap: 16px;
    height: 60px; padding: 0 24px;
    background: #1e293b; border-top: 1px solid #334155;
    flex-shrink: 0;
  }

  

  .scrubber-container {
    flex: 1; display: flex; align-items: center; gap: 16px;
  }
  .time-readout {
    font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
    font-weight: 500; color: #e2e8f0; width: 80px;
  }


  /* Custom Range Slider */
  .scrubber {
    flex: 1; -webkit-appearance: none; appearance: none;
    height: 6px; background: #0f172a; border-radius: 3px;
    outline: none; border: 1px solid #334155; cursor: pointer;
  }
  .scrubber::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none;
    width: 14px; height: 14px; border-radius: 50%;
    background: #38bdf8; cursor: pointer;
    box-shadow: 0 0 8px rgba(56, 189, 248, 0.5);
  }
  .scrubber::-moz-range-thumb {
    width: 14px; height: 14px; border-radius: 50%;
    background: #38bdf8; cursor: pointer; border: none;
  }
</style>