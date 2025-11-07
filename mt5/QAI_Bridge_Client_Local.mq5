//+------------------------------------------------------------------+
//|                                       QAI_Bridge_Client_Local.mq5 |
//|                            QAI Trader Bridge EA - LOCALHOST MODE |
//|                        Optimized for same-PC bridge (127.0.0.1) |
//+------------------------------------------------------------------+
#property copyright "QAI Trader"
#property link      "https://github.com/codexia87-glitch/qai-trader"
#property version   "1.10"
#property description "Bridge client optimized for localhost (Windows all-in-one)"
#property strict

//--- Input parameters
input string BridgeHost = "127.0.0.1";       // Bridge server IP (localhost)
input int    BridgePort = 8443;              // Bridge server port
input string QAI_Token = "w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo"; // Auth token
input int    PollIntervalSeconds = 5;        // Polling interval (seconds)
input int    Slippage = 10;                  // Max slippage in points
input bool   EnableFeedback = true;          // Send execution feedback
input string AllowedSymbols = "EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,XAUUSD"; // Whitelist
input string LogPrefix = "[QAI-Local]";      // Log prefix

//--- Global variables
datetime lastPollTime = 0;
int pollIntervalMs;
string bridgeUrl;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   pollIntervalMs = PollIntervalSeconds * 1000;
   bridgeUrl = "http://" + BridgeHost + ":" + IntegerToString(BridgePort);
   
   // Validate inputs
   if(StringLen(QAI_Token) == 0)
   {
      Print(LogPrefix, " ERROR: QAI_Token is empty!");
      return INIT_PARAMETERS_INCORRECT;
   }
   
   // Log mode
   Print(LogPrefix, " ================================");
   Print(LogPrefix, " QAI Bridge Client - LOCALHOST MODE");
   Print(LogPrefix, " ================================");
   Print(LogPrefix, " Bridge URL: ", bridgeUrl);
   Print(LogPrefix, " Poll interval: ", PollIntervalSeconds, " seconds");
   Print(LogPrefix, " Allowed symbols: ", AllowedSymbols);
   Print(LogPrefix, " ================================");
   
   // Test connection
   if(!TestConnection())
   {
      Print(LogPrefix, " WARNING: Could not connect to bridge server");
      Print(LogPrefix, " Check that:");
      Print(LogPrefix, "   1. Bridge server is running: start_bridge_server.ps1");
      Print(LogPrefix, "   2. BridgeHost is correct: ", BridgeHost);
      Print(LogPrefix, "   3. URL is in MT5 WebRequest whitelist");
      Print(LogPrefix, "   4. Python script is running on same PC");
      Print(LogPrefix, " EA will continue trying to connect...");
   }
   else
   {
      Print(LogPrefix, " ✓ Successfully connected to bridge server");
      Print(LogPrefix, " ✓ Localhost mode active (low latency)");
   }
   
   lastPollTime = TimeCurrent();
   
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print(LogPrefix, " EA stopped. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   // Poll bridge server at regular intervals
   datetime now = TimeCurrent();
   
   if((now - lastPollTime) >= PollIntervalSeconds)
   {
      lastPollTime = now;
      CheckForSignals();
   }
}

//+------------------------------------------------------------------+
//| Test connection to bridge server                                   |
//+------------------------------------------------------------------+
bool TestConnection()
{
   string url = bridgeUrl + "/health";
   string headers = "X-QAI-Token: " + QAI_Token + "\r\n";
   
   char post[];
   char result[];
   string resultHeaders;
   
   ResetLastError();
   int res = WebRequest(
      "GET",
      url,
      headers,
      5000,  // 5 second timeout
      post,
      result,
      resultHeaders
   );
   
   if(res == -1)
   {
      int error = GetLastError();
      Print(LogPrefix, " WebRequest error: ", error);
      
      if(error == 4060)
      {
         Print(LogPrefix, " ERROR: URL not allowed in WebRequest whitelist!");
         Print(LogPrefix, " Add this to Tools -> Options -> Expert Advisors:");
         Print(LogPrefix, "   http://127.0.0.1:8443");
      }
      
      return false;
   }
   
   if(res == 200)
   {
      string response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
      Print(LogPrefix, " Health check OK (localhost): ", StringSubstr(response, 0, 100));
      return true;
   }
   
   Print(LogPrefix, " Health check failed with status: ", res);
   return false;
}

//+------------------------------------------------------------------+
//| Check for new signals from bridge                                 |
//+------------------------------------------------------------------+
void CheckForSignals()
{
   string url = bridgeUrl + "/next";
   string headers = "X-QAI-Token: " + QAI_Token + "\r\n";
   
   char post[];
   char result[];
   string resultHeaders;
   
   ResetLastError();
   int res = WebRequest(
      "GET",
      url,
      headers,
      10000,  // 10 second timeout
      post,
      result,
      resultHeaders
   );
   
   if(res == -1)
   {
      int error = GetLastError();
      Print(LogPrefix, " WebRequest error: ", error);
      return;
   }
   
   if(res == 401 || res == 403)
   {
      Print(LogPrefix, " Authentication failed! Check QAI_Token");
      return;
   }
   
   if(res != 200)
   {
      Print(LogPrefix, " Bridge returned status: ", res);
      return;
   }
   
   // Parse response
   string response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   
   // Check if queue is empty
   if(StringFind(response, "\"status\":\"empty\"") >= 0 ||
      StringFind(response, "\"status\": \"empty\"") >= 0)
   {
      // Queue empty - this is normal, no log spam
      return;
   }
   
   // We have a signal!
   Print(LogPrefix, " ✓ Signal received from localhost");
   ProcessSignal(response);
}

//+------------------------------------------------------------------+
//| Process and execute signal                                         |
//+------------------------------------------------------------------+
void ProcessSignal(string jsonResponse)
{
   // Parse JSON manually (MQL5 doesn't have built-in JSON parser)
   string symbol = ExtractJsonString(jsonResponse, "symbol");
   string side = ExtractJsonString(jsonResponse, "side");
   double volume = ExtractJsonDouble(jsonResponse, "volume");
   double price = ExtractJsonDouble(jsonResponse, "price");
   int sl_pts = (int)ExtractJsonDouble(jsonResponse, "sl_pts");
   int tp_pts = (int)ExtractJsonDouble(jsonResponse, "tp_pts");
   string signal_id = ExtractJsonString(jsonResponse, "id");
   
   // Validate
   if(StringLen(symbol) == 0 || StringLen(side) == 0 || volume <= 0)
   {
      Print(LogPrefix, " Invalid signal format!");
      return;
   }
   
   // Check if symbol is allowed
   if(!IsSymbolAllowed(symbol))
   {
      Print(LogPrefix, " Symbol NOT allowed: ", symbol);
      Print(LogPrefix, " Allowed symbols: ", AllowedSymbols);
      SendFeedback(signal_id, "rejected", 0, 0.0, "Symbol not in whitelist");
      return;
   }
   
   Print(LogPrefix, " Executing: ", side, " ", volume, " ", symbol);
   
   // Execute the order
   ExecuteOrder(symbol, side, volume, price, sl_pts, tp_pts, signal_id);
}

//+------------------------------------------------------------------+
//| Check if symbol is in allowed list                                |
//+------------------------------------------------------------------+
bool IsSymbolAllowed(string symbol)
{
   if(StringLen(AllowedSymbols) == 0)
      return true;  // Empty whitelist = allow all
   
   // Check if symbol appears in comma-separated list
   return (StringFind(AllowedSymbols, symbol) >= 0);
}

//+------------------------------------------------------------------+
//| Execute market order                                               |
//+------------------------------------------------------------------+
void ExecuteOrder(string symbol, string side, double volume, double price,
                  int sl_pts, int tp_pts, string signal_id)
{
   // Prepare trade request
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   
   // Try to select symbol with common broker suffixes
   string actualSymbol = ResolveSymbol(symbol);
   if(StringLen(actualSymbol) == 0)
   {
      Print(LogPrefix, " ERROR: Symbol not available: ", symbol);
      SendFeedback(signal_id, "failed", 0, 0.0, "Symbol not available");
      return;
   }
   
   // Get symbol info
   double point = SymbolInfoDouble(actualSymbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(actualSymbol, SYMBOL_DIGITS);
   double tick_size = SymbolInfoDouble(actualSymbol, SYMBOL_TRADE_TICK_SIZE);
   double min_lot = SymbolInfoDouble(actualSymbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(actualSymbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(actualSymbol, SYMBOL_VOLUME_STEP);
   
   // Validate volume
   if(volume < min_lot)
   {
      Print(LogPrefix, " Volume too small, using minimum: ", min_lot);
      volume = min_lot;
   }
   if(volume > max_lot)
   {
      Print(LogPrefix, " Volume too large, using maximum: ", max_lot);
      volume = max_lot;
   }
   
   // Determine order type and price
   ENUM_ORDER_TYPE orderType;
   double orderPrice;
   
   if(side == "BUY")
   {
      orderType = ORDER_TYPE_BUY;
      orderPrice = SymbolInfoDouble(actualSymbol, SYMBOL_ASK);
   }
   else if(side == "SELL")
   {
      orderType = ORDER_TYPE_SELL;
      orderPrice = SymbolInfoDouble(actualSymbol, SYMBOL_BID);
   }
   else
   {
      Print(LogPrefix, " ERROR: Invalid side: ", side);
      SendFeedback(signal_id, "failed", 0, 0.0, "Invalid side");
      return;
   }
   
   // Calculate SL and TP
   double sl_price = 0.0;
   double tp_price = 0.0;
   
   if(sl_pts > 0)
   {
      if(side == "BUY")
         sl_price = NormalizeDouble(orderPrice - sl_pts * point, digits);
      else
         sl_price = NormalizeDouble(orderPrice + sl_pts * point, digits);
   }
   
   if(tp_pts > 0)
   {
      if(side == "BUY")
         tp_price = NormalizeDouble(orderPrice + tp_pts * point, digits);
      else
         tp_price = NormalizeDouble(orderPrice - tp_pts * point, digits);
   }
   
   // Fill request
   request.action = TRADE_ACTION_DEAL;
   request.symbol = actualSymbol;
   request.volume = volume;
   request.type = orderType;
   request.price = orderPrice;
   request.sl = sl_price;
   request.tp = tp_price;
   request.deviation = Slippage;
   request.magic = 20251107;  // Updated magic number
   request.comment = "QAI-Local-" + signal_id;
   request.type_filling = ORDER_FILLING_IOC;
   
   // Try different filling modes
   if(!OrderSend(request, result))
   {
      request.type_filling = ORDER_FILLING_FOK;
      if(!OrderSend(request, result))
      {
         request.type_filling = ORDER_FILLING_RETURN;
         OrderSend(request, result);
      }
   }
   
   // Check result
   if(result.retcode == TRADE_RETCODE_DONE || result.retcode == TRADE_RETCODE_PLACED)
   {
      Print(LogPrefix, " ✓ Order executed successfully!");
      Print(LogPrefix, "   Ticket: ", result.order);
      Print(LogPrefix, "   Price: ", result.price);
      Print(LogPrefix, "   Volume: ", result.volume);
      Print(LogPrefix, "   Symbol: ", actualSymbol);
      
      SendFeedback(signal_id, "executed", result.order, result.price, "Success");
   }
   else
   {
      Print(LogPrefix, " ✗ Order failed!");
      Print(LogPrefix, "   Retcode: ", result.retcode);
      Print(LogPrefix, "   Comment: ", result.comment);
      
      SendFeedback(signal_id, "failed", 0, 0.0, 
                   "Retcode: " + IntegerToString(result.retcode) + " - " + result.comment);
   }
}

//+------------------------------------------------------------------+
//| Resolve symbol with broker suffixes                               |
//+------------------------------------------------------------------+
string ResolveSymbol(string baseSymbol)
{
   // Try base symbol first
   if(SymbolSelect(baseSymbol, true))
      return baseSymbol;
   
   // Try common suffixes
   string suffixes[] = {".m", ".i", ".pro", ".raw", ".ecn", "_sb"};
   
   for(int i = 0; i < ArraySize(suffixes); i++)
   {
      string testSymbol = baseSymbol + suffixes[i];
      if(SymbolSelect(testSymbol, true))
      {
         Print(LogPrefix, " Symbol resolved: ", baseSymbol, " -> ", testSymbol);
         return testSymbol;
      }
   }
   
   return "";  // Not found
}

//+------------------------------------------------------------------+
//| Send execution feedback to bridge                                 |
//+------------------------------------------------------------------+
void SendFeedback(string signal_id, string status, ulong ticket, 
                  double execution_price, string message)
{
   if(!EnableFeedback)
      return;
   
   string url = bridgeUrl + "/feedback";
   string headers = "X-QAI-Token: " + QAI_Token + "\r\n";
   headers += "Content-Type: application/json\r\n";
   
   // Build JSON payload
   string json = "{";
   json += "\"signal_id\":\"" + signal_id + "\",";
   json += "\"status\":\"" + status + "\",";
   json += "\"order_ticket\":" + IntegerToString(ticket) + ",";
   json += "\"execution_price\":" + DoubleToString(execution_price, 5) + ",";
   json += "\"message\":\"" + message + "\",";
   json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\"";
   json += "}";
   
   char post[];
   StringToCharArray(json, post, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   
   char result[];
   string resultHeaders;
   
   ResetLastError();
   int res = WebRequest(
      "POST",
      url,
      headers,
      5000,
      post,
      result,
      resultHeaders
   );
   
   if(res == 200)
   {
      Print(LogPrefix, " ✓ Feedback sent to localhost");
   }
   else
   {
      Print(LogPrefix, " Failed to send feedback. Status: ", res);
   }
}

//+------------------------------------------------------------------+
//| Simple JSON string extractor                                      |
//+------------------------------------------------------------------+
string ExtractJsonString(string json, string key)
{
   string searchKey = "\"" + key + "\"";
   int pos = StringFind(json, searchKey);
   if(pos < 0)
      return "";
   
   pos = StringFind(json, ":", pos);
   if(pos < 0)
      return "";
   
   pos++;
   while(pos < StringLen(json) && (StringGetCharacter(json, pos) == ' ' || 
                                     StringGetCharacter(json, pos) == '\"'))
      pos++;
   
   int endPos = pos;
   while(endPos < StringLen(json))
   {
      ushort ch = StringGetCharacter(json, endPos);
      if(ch == '\"' || ch == ',' || ch == '}')
         break;
      endPos++;
   }
   
   return StringSubstr(json, pos, endPos - pos);
}

//+------------------------------------------------------------------+
//| Simple JSON number extractor                                      |
//+------------------------------------------------------------------+
double ExtractJsonDouble(string json, string key)
{
   string searchKey = "\"" + key + "\"";
   int pos = StringFind(json, searchKey);
   if(pos < 0)
      return 0.0;
   
   pos = StringFind(json, ":", pos);
   if(pos < 0)
      return 0.0;
   
   pos++;
   while(pos < StringLen(json) && StringGetCharacter(json, pos) == ' ')
      pos++;
   
   if(StringSubstr(json, pos, 4) == "null")
      return 0.0;
   
   int endPos = pos;
   while(endPos < StringLen(json))
   {
      ushort ch = StringGetCharacter(json, endPos);
      if((ch < '0' || ch > '9') && ch != '.' && ch != '-')
         break;
      endPos++;
   }
   
   string numStr = StringSubstr(json, pos, endPos - pos);
   return StringToDouble(numStr);
}
//+------------------------------------------------------------------+
