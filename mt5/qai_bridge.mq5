//+------------------------------------------------------------------+
//| qai_bridge.mq5                                                  |
//| Minimal MQL5 Expert Advisor (EA) stub for Sprint 1 bridge      |
//| Purpose: placeholder that documents how MetaTrader would read  |
//| .sig files produced by Python and translate them to orders.    |
//+------------------------------------------------------------------+
#property copyright "(c) qai-trader"
#property version   "0.1"
// Note: This file is a documentation-level stub. It contains no
// operational trading logic and should NOT be run on live accounts.

// --- Design notes ---
// 1) This EA is expected to watch a configured directory for files
//    with extension ".sig" (simple text signals) written by the
//    Python bridge. When a new signal appears, the EA parses it and
//    executes the corresponding trading action (market order, limit,
//    close, etc.).
// 2) For Sprint 1 we only provide the skeleton and comments.
// 3) Later: consider using file timestamps + atomic renames to avoid
//    partial-read races, or use a socket/native bridge if performance
//    is needed.

//--- configuration (placeholders) ---------------------------------
input string SignalsFolder = "MQL5\Files\qai_signals"; // relative to Terminal\MQL5\Files

//+------------------------------------------------------------------+
int OnInit()
  {
   // TODO: Validate SignalsFolder exists and attempt to create it if needed.
   Print("qai_bridge EA initialized. SignalsFolder=",SignalsFolder);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   // Cleanup if needed
   Print("qai_bridge EA deinitialized.");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
  // Placeholder: In a real EA, we would periodically check SignalsFolder
  // for new signal files, parse them and execute orders accordingly.
  // The recommended flow is:
  //  1) Check for JSON signals first (*.sig.json). If none found,
  //     fall back to legacy key=value files (*.sig).
  //  2) For each candidate file:
  //      - Open and read the file atomically (avoid partial reads).
  //      - Parse JSON or key=value content.
  //      - Validate required fields and risk constraints.
  //      - Execute order via OrderSend/PositionOpen/PositionClose.
  //      - Move the processed file to an "archived" subfolder.
  //      - On parse/error, move to "failed" for manual inspection.

  // --- Example pseudo-code (not runnable MQL5; for guidance only) ---
  // string files[] = ListFiles(SignalsFolder, "*.sig.json");
  // if(ArraySize(files) == 0)
  //     files = ListFiles(SignalsFolder, "*.sig");
  // for(int i=0;i<ArraySize(files);++i)
  // {
  //     string fname = files[i];
  //     // Use FileOpen with FILE_READ|FILE_ANSI (or FILE_BIN) depending on encoding
  //     int fh = FileOpen(SignalsFolder + "\\" + fname, FILE_READ|FILE_ANSI);
  //     if(fh == INVALID_HANDLE)
  //     {
  //         // handle error, continue
  //         continue;
  //     }
  //     string raw = FileReadString(fh);
  //     FileClose(fh);
  //
  //     // If JSON file
  //     if(StringFind(fname, ".sig.json") >= 0)
  //     {
  //         // Parse JSON: MQL5 has JsonParser classes in some libs; if not
  //         // implement a small lightweight JSON parser or call an external
  //         // helper. Example (pseudo):
  //         // CJAsonParser parser; parser.Parse(raw);
  //         // string symbol = parser.GetString("symbol");
  //         // string side = parser.GetString("side");
  //         // double volume = parser.GetDouble("volume");
  //     }
  //     else // legacy key=value
  //     {
  //         // Simple parse: split lines on '\n', then split on '='
  //         // for each non-empty line: key,value = StringSplit(line, "=");
  //     }
  //
  //     // Validate and apply basic risk checks (max size, allowed symbols, etc.)
  //     // if not valid: MoveFile(SignalsFolder+"\\"+fname, SignalsFolder+"\\failed\\"+fname);
  //
  //     // Example order send (simplified):
  //     // if(side=="BUY") OrderSend(symbol, OP_BUY, volume, Ask, slippage, sl, tp, comment);
  //     // else if(side=="SELL") OrderSend(symbol, OP_SELL, volume, Bid, slippage, sl, tp, comment);
  //
  //     // After successful execution move to archive
  //     // MoveFile(SignalsFolder+"\\"+fname, SignalsFolder+"\\archived\\"+fname);
  // }

  // --- Implementation notes and cautions ---
  // - Atomicity: Python writes files atomically (temp -> rename). On MT5
  //   side prefer checking for close-to-final names and ignore files
  //   that are still being written. For robust operation consider a
  //   small "lock" convention (e.g., write .ready file) or use the
  //   atomic rename strategy as already implemented on the Python side.
  // - Encoding: ensure Python writes UTF-8 and use the correct FileOpen
  //   flags in MQL5 (FILE_ANSI vs FILE_UNICODE). Test with sample files.
  // - JSON parsing: MQL5 does not include a rich stdlib JSON parser in
  //   all environments; consider shipping a small parser or invoking a
  //   local helper process if necessary.
  // - Security: only trust signals from a controlled folder; consider
  //   HMAC signatures or filesystem ACLs in production.
  }

//+------------------------------------------------------------------+
// End of stub
//+------------------------------------------------------------------+
