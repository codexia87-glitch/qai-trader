//+------------------------------------------------------------------+
//|                                              QAI_Bridge_Client.mq5 |
//|                                       QAI Trader Bridge EA Client |
//|                                              Real-time MT5 Client |
//+------------------------------------------------------------------+
#property copyright "QAI Trader"
#property link      "https://github.com/codexia87-glitch/qai-trader"
#property version   "1.00"
#property strict

//--- Input parameters
input string BridgeHost = "192.168.0.100";  // Bridge server IP (Mac LAN)
input int    BridgePort = 8443;              // Bridge server port
input string QAI_Token = "w58xH_gKg1vL9e6aZKw7TXY8hOjnZ30f-akjyREPkJo"; // Auth token
input int    PollIntervalSeconds = 5;        // Polling interval (seconds)
input int    Slippage = 10;                  // Max slippage in points
input bool   EnableFeedback = true;          // Send execution feedback
input string LogPrefix = "[QAI-Bridge]";     // Log prefix

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
   
   if(StringLen(BridgeHost) == 0)
   {
      Print(LogPrefix, " ERROR: BridgeHost is empty!");
      return INIT_PARAMETERS_INCORRECT;
   }
   
   // Test connection
   Print(LogPrefix, " Initializing...");
   Print(LogPrefix, " Bridge URL: ", bridgeUrl);
   Print(LogPrefix, " Poll interval: ", PollIntervalSeconds, " seconds");
   
   if(!TestConnection())
   {
      Print(LogPrefix, " WARNING: Could not connect to bridge server");
      Print(LogPrefix, " Check that:");
      Print(LogPrefix, "   1. Bridge server is running on Mac");
      Print(LogPrefix, "   2. BridgeHost IP is correct: ", BridgeHost);
      Print(LogPrefix, "   3. URL is in MT5 WebRequest whitelist");
      Print(LogPrefix, " EA will continue trying to connect...");
   }
   else
   {
      Print(LogPrefix, " Successfully connected to bridge server");
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
         Print(LogPrefix, "   ", url);
      }
      
      return false;
   }
   
   if(res == 200)
   {
      string response = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
      Print(LogPrefix, " Health check OK: ", response);
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
   Print(LogPrefix, " Received signal: ", response);
   ProcessSignal(response);
}

//+------------------------------------------------------------------+
//| Process and execute signal                                         |
//+------------------------------------------------------------------+
void ProcessSignal(string jsonResponse)
{
   // Parse JSON manually (MQL5 doesn't have built-in JSON parser)
   // This is a simple parser for our specific format
   
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
   
   Print(LogPrefix, " Executing: ", side, " ", volume, " ", symbol);
   
   // Execute the order
   ExecuteOrder(symbol, side, volume, price, sl_pts, tp_pts, signal_id);
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
   
   // Set symbol
   if(!SymbolSelect(symbol, true))
   {
      Print(LogPrefix, " ERROR: Could not select symbol: ", symbol);
      SendFeedback(signal_id, "failed", 0, 0.0, "Symbol not available");
      return;
   }
   
   // Get symbol info
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   double tick_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double min_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   
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
      orderPrice = SymbolInfoDouble(symbol, SYMBOL_ASK);
   }
   else if(side == "SELL")
   {
      orderType = ORDER_TYPE_SELL;
      orderPrice = SymbolInfoDouble(symbol, SYMBOL_BID);
   }
   else
   {
      Print(LogPrefix, " ERROR: Invalid side: ", side);
      SendFeedback(signal_id, "failed", 0, 0.0, "Invalid side");
      return;
   }
   
   // If signal specifies price, use it (limit order logic could go here)
   // For now we do market orders
   
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
   request.symbol = symbol;
   request.volume = volume;
   request.type = orderType;
   request.price = orderPrice;
   request.sl = sl_price;
   request.tp = tp_price;
   request.deviation = Slippage;
   request.magic = 20251106;  // QAI magic number
   request.comment = "QAI-" + signal_id;
   request.type_filling = ORDER_FILLING_IOC;
   
   // Try different filling modes if IOC fails
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
      Print(LogPrefix, " Order executed successfully!");
      Print(LogPrefix, "   Ticket: ", result.order);
      Print(LogPrefix, "   Price: ", result.price);
      Print(LogPrefix, "   Volume: ", result.volume);
      
      SendFeedback(signal_id, "executed", result.order, result.price, "Success");
   }
   else
   {
      Print(LogPrefix, " Order failed!");
      Print(LogPrefix, "   Retcode: ", result.retcode);
      Print(LogPrefix, "   Comment: ", result.comment);
      
      SendFeedback(signal_id, "failed", 0, 0.0, 
                   "Retcode: " + IntegerToString(result.retcode) + " - " + result.comment);
   }
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
   ArrayResize(post, ArraySize(post) - 1); // Remove null terminator
   
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
      Print(LogPrefix, " Feedback sent successfully");
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
   
   // Find the value after the colon
   pos = StringFind(json, ":", pos);
   if(pos < 0)
      return "";
   
   // Skip whitespace and quotes
   pos++;
   while(pos < StringLen(json) && (StringGetCharacter(json, pos) == ' ' || 
                                     StringGetCharacter(json, pos) == '\"'))
      pos++;
   
   // Extract until quote or comma
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
   
   // Find the value after the colon
   pos = StringFind(json, ":", pos);
   if(pos < 0)
      return 0.0;
   
   // Skip whitespace
   pos++;
   while(pos < StringLen(json) && StringGetCharacter(json, pos) == ' ')
      pos++;
   
   // Check for null
   if(StringSubstr(json, pos, 4) == "null")
      return 0.0;
   
   // Extract number string
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
