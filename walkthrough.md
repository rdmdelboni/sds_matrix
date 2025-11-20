# App Evaluation Report

## Overview
The FDS Reader is a Python-based desktop application for extracting data from Safety Data Sheets (FDS). It uses a hybrid approach with local heuristics and optional LLM (Ollama/Gemini) integration.

## Status
- **Tests**: ✅ 90/90 tests passed.
- **Code Quality**: Good modular structure. High coverage in core logic.
- **Dependencies**: Standard and up-to-date.
- **CLI**: Functional, successfully processed example files.

## Critical Findings
### 🐛 Bug: UN Number False Positive (Fixed)
The heuristic extraction for "Numero ONU" was too aggressive, matching years, phone numbers, and densities.
- **Fix Applied**: Updated `heuristics.py` with strict filters:
    - **Global Phone Masking**: Implemented `_mask_phone_numbers` to replace phone patterns (0800, +XX, (XX)) with `[PHONE]` before processing.
    - **Year Filtering**: Improved to ignore years (1900-2100) in date contexts, including month names (e.g. "novembro de 2022").
    - **Decimal Filtering**: Ignore decimal parts (preceded by , or .).
    - **CAS Filtering**: Ignore parts of CAS numbers.
- **Status**:
    - ✅ `7HF_FDS_Portugues.pdf`: Correctly extracts **1075**.
    - ✅ `FDS-OEM...`: Correctly returns **NAO ENCONTRADO** (file states "não aplicável").
    - ✅ `841578_SDS_BR_Z9.PDF`: Correctly extracts **2433** (previously masked by false positives).
- **App Startup**: Verified `main.py` starts successfully without errors.

### 🚀 Improvement: Class Extraction
- **Implemented**: Added `UN_CLASS_MAP` to infer class from UN number.
- **Status**:
    - ✅ `7HF_FDS_Portugues.pdf`: Now correctly infers Class **2.1** from UN 1075.
    - ✅ `841578_SDS_BR_Z9.PDF`: Now correctly infers Class **6.1** from UN 2433.

## Recommendations
1.  **Future Improvements**:
    -   Expand `UN_CLASS_MAP` further as needed.
    -   Consider using LLM for final validation of extracted fields if heuristics have low confidence.

## Conclusion
The critical UN Number extraction bug has been resolved by implementing a robust set of heuristics including global phone number masking, context-aware year filtering, and decimal exclusion. Additionally, the Class Extraction has been significantly improved using a lookup table. The application is now correctly extracting data from the provided example files.

## Next Steps
- **Monitor**: Watch for new edge cases in production files.
- **LLM Integration**: Re-enable LLM extraction to see if it complements the improved heuristics.
