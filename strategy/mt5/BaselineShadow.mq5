#property strict
#property version "1.000"
#property description "Demo observation only: closed M15 signals and equity guard. No orders."

input int ChannelBars = 20;
input int AtrBars = 14;
input double InternalDrawdown = 0.10;
input double CompetitionDrawdown = 0.20;

int output = INVALID_HANDLE;
long bound_login = 0;
string bound_server = "";
string state_key = "";
double peak_equity = 0;
bool halted = false;
bool state_ready = false;
datetime last_closed = 0;

uint ServerHash(const string value)
{
   uint hash = 2166136261;
   for(int i=0; i<StringLen(value); i++)
      hash = (hash ^ (uint)StringGetCharacter(value, i)) * 16777619;
   return hash;
}

bool StoreState()
{
   if(GlobalVariableSet(state_key+".peak", peak_equity)==0 ||
      GlobalVariableSet(state_key+".halt", halted ? 1.0 : 0.0)==0 ||
      GlobalVariableSet(state_key+".dd", InternalDrawdown)==0)
      return false;
   GlobalVariablesFlush();
   return true;
}

void ObserveEquity()
{
   if(AccountInfoInteger(ACCOUNT_LOGIN)!=bound_login || AccountInfoString(ACCOUNT_SERVER)!=bound_server)
   {
      halted = true;
      return;
   }
   const double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!MathIsValidNumber(equity) || equity<=0)
   {
      halted = true;
      StoreState();
      return;
   }
   const double old_peak = peak_equity;
   const bool old_halt = halted;
   peak_equity = MathMax(peak_equity, equity);
   if(equity <= peak_equity*(1.0-InternalDrawdown))
      halted = true;
   if((old_peak!=peak_equity || old_halt!=halted) && !StoreState())
      halted = true;
}

int OnInit()
{
   if(ChannelBars<1 || AtrBars<1 || !MathIsValidNumber(InternalDrawdown) ||
      !MathIsValidNumber(CompetitionDrawdown) || InternalDrawdown<=0 ||
      InternalDrawdown>=CompetitionDrawdown || CompetitionDrawdown>=1)
      return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO ||
      AccountInfoString(ACCOUNT_CURRENCY)!="USD" ||
      SymbolInfoString(_Symbol, SYMBOL_CURRENCY_BASE)!="EUR" ||
      SymbolInfoString(_Symbol, SYMBOL_CURRENCY_PROFIT)!="USD")
   {
      Print("SHADOW_REFUSED: requires EURUSD and an existing USD demo account");
      return INIT_FAILED;
   }
   bound_login = AccountInfoInteger(ACCOUNT_LOGIN);
   bound_server = AccountInfoString(ACCOUNT_SERVER);
   state_key = StringFormat("BShadow1.%I64d.%u", bound_login, ServerHash(bound_server));
   const bool has_peak = GlobalVariableCheck(state_key+".peak");
   const bool has_halt = GlobalVariableCheck(state_key+".halt");
   const bool has_dd = GlobalVariableCheck(state_key+".dd");
   if(has_peak || has_halt || has_dd)
   {
      if(!has_peak || !has_halt || !has_dd || GlobalVariableGet(state_key+".dd")!=InternalDrawdown)
         return INIT_FAILED;
      peak_equity = GlobalVariableGet(state_key+".peak");
      const double saved_halt = GlobalVariableGet(state_key+".halt");
      if(!MathIsValidNumber(peak_equity) || peak_equity<=0 || (saved_halt!=0 && saved_halt!=1))
         return INIT_FAILED;
      halted = saved_halt==1;
   }
   else
      peak_equity = MathMax(AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   if(!MathIsValidNumber(peak_equity) || peak_equity<=0 || !StoreState())
      return INIT_FAILED;
   state_ready = true;
   output = FileOpen(state_key+".csv", FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ, ',');
   if(output==INVALID_HANDLE)
      return INIT_FAILED;
   if(FileSize(output)==0)
      FileWrite(output, "server_time", "event", "closed_bar", "side", "atr", "spread_points", "equity", "observed_peak", "internal_floor", "halted");
   FileSeek(output, 0, SEEK_END);
   // Do not emit an old entry signal merely because this EA was attached/restarted.
   last_closed = iTime(_Symbol, PERIOD_M15, 1);
   if(!EventSetTimer(5))
      return INIT_FAILED;
   Print("SHADOW_INIT: no order execution; peak starts at first observed equity unless persisted");
   return INIT_SUCCEEDED;
}

void LogEvent(const string event, const datetime closed_bar, const int side, const double atr)
{
   FileWrite(output, TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS), event,
             (long)closed_bar, side, DoubleToString(atr, 8), SymbolInfoInteger(_Symbol, SYMBOL_SPREAD),
             DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2), DoubleToString(peak_equity, 2),
             DoubleToString(peak_equity*(1.0-InternalDrawdown), 2), halted);
   FileFlush(output);
}

void OnTick()
{
   ObserveEquity();
   if(AccountInfoInteger(ACCOUNT_LOGIN)!=bound_login || AccountInfoString(ACCOUNT_SERVER)!=bound_server)
      return;
   const datetime closed_bar = iTime(_Symbol, PERIOD_M15, 1);
   if(closed_bar<=0 || closed_bar==last_closed)
      return;
   MqlRates rates[];
   ArraySetAsSeries(rates, false);
   const int needed = MathMax(ChannelBars, AtrBars)+1;
   if(CopyRates(_Symbol, PERIOD_M15, 1, needed, rates)!=needed)
      return;
   if(rates[needed-1].time!=closed_bar)
      return;
   last_closed = closed_bar;
   double upper = rates[needed-2].high;
   double lower = rates[needed-2].low;
   for(int i=needed-ChannelBars-1; i<needed-1; i++)
   {
      upper = MathMax(upper, rates[i].high);
      lower = MathMin(lower, rates[i].low);
   }
   int side = 0;
   if(rates[needed-1].close>upper) side=1;
   if(rates[needed-1].close<lower) side=-1;
   double atr = 0;
   for(int i=needed-AtrBars; i<needed; i++)
      atr += MathMax(rates[i].high-rates[i].low,
                     MathMax(MathAbs(rates[i].high-rates[i-1].close), MathAbs(rates[i].low-rates[i-1].close)));
   atr /= AtrBars;
   LogEvent(halted ? "blocked-risk" : (side==0 ? "bar" : "signal-only"), closed_bar, side, atr);
}

void OnTimer()
{
   ObserveEquity();
   LogEvent("heartbeat", 0, 0, 0);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(state_ready) StoreState();
   if(output!=INVALID_HANDLE) FileClose(output);
}
