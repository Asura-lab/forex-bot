#property strict
#property version "1.00"
#property description "Runtime verification only. Contains no order or account modification calls."

int heartbeat_file = INVALID_HANDLE;
ulong tick_count = 0;
ulong timer_count = 0;
ulong previous_timer_ms = 0;

int OnInit()
{
   heartbeat_file = FileOpen("runtime-probe.csv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ, ',');
   if(heartbeat_file == INVALID_HANDLE)
      return INIT_FAILED;
   FileWrite(heartbeat_file, "wall_time", "uptime_ms", "timer_count", "timer_gap_ms", "tick_count", "connected", "terminal_memory_mb", "mql_memory_mb", "calculation_us", "checksum");
   if(!EventSetTimer(1))
      return INIT_FAILED;
   previous_timer_ms = GetTickCount64();
   Print("RUNTIME_PROBE_INIT build=", TerminalInfoInteger(TERMINAL_BUILD), " symbol=", _Symbol);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   tick_count++;
}

void OnTimer()
{
   const ulong now_ms = GetTickCount64();
   const ulong started_us = GetMicrosecondCount();
   double checksum = 0;
   // Fixed synthetic calculation load; no training or trade execution.
   for(int i=1; i<=10000; i++)
      checksum += MathSin((double)i / 100.0) * MathSqrt((double)i);
   const ulong calculation_us = GetMicrosecondCount() - started_us;
   timer_count++;
   FileWrite(heartbeat_file, TimeToString(TimeLocal(), TIME_DATE|TIME_SECONDS), now_ms, timer_count,
             now_ms - previous_timer_ms, tick_count, TerminalInfoInteger(TERMINAL_CONNECTED),
             TerminalInfoInteger(TERMINAL_MEMORY_USED), MQLInfoInteger(MQL_MEMORY_USED),
             calculation_us, DoubleToString(checksum, 8));
   FileFlush(heartbeat_file);
   previous_timer_ms = now_ms;
   if(timer_count % 60 == 0)
      Print("RUNTIME_PROBE_HEARTBEAT timer=", timer_count, " ticks=", tick_count);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(heartbeat_file != INVALID_HANDLE)
      FileClose(heartbeat_file);
   Print("RUNTIME_PROBE_STOP reason=", reason);
}
