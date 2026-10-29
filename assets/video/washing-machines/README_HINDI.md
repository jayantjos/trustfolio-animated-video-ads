# TrustFolio Washing Machine — Approved Source Voice Master Kit

## ZIP की जाँच
- Upload में 12 MP4 थे; 4 दस-सेकंड की Green Boy files byte-for-byte identical थीं। इस kit में 9 unique clips हैं।
- हर clip की ORIGINAL आवाज़ `assets/audio/original/*.wav` में lossless PCM में निकाली है। आवाज़ बदलने या synthetic clone बनाने का दावा नहीं है।
- `assets/reference_frames` में हर clip का image reference है। `config/source_inventory.json` में SHA256, original names, length दर्ज है।
- Videos 360×640 portrait हैं, final 720×1280 project में upscale की जरूरत होगी।

## सबसे महत्वपूर्ण design decision
**Existing spoken MP4 का dialogue dynamic नहीं हो सकता।** Original voices को immutable, approved references की तरह रखें। बदलते product names/specs के लिए उसी voice identity से नया TTS audio बनाना होगा (rights/permission and suitable voice system), फिर audio-driven lip-sync rerender; या character का मुंह बंद/voiceover style रखकर original animation reuse करें। Original fixed dialogue और नई narration एक साथ नहीं बजानी।

## काम का flow
1. Live API पर category/budget(+brand)/comparison input; 5 product IDs लेकर current price+availability validate करें।
2. ₹budget से ऊपर या unavailable/OOS item को replace करें; पर्याप्त 5 ना हों तो skip करें, invented/fallback price न दिखाएँ।
3. Verified product JSON validate करें (names, price, product image, four specs, rank) और source snapshot timestamp save करें।
4. Product compositor: `08_green_boy_clean_master.mp4` के EMPTY RIGHT PANEL में product photo/text render करें। Overlay को actual measurements के हिसाब से fit करें; baked-in text वाली `07_green_boy_product_demo.mp4` को blindly dynamic data के लिए reuse नहीं करना।
5. Narration dynamic बनानी हो तो approved consistent Hindi voice synthesizer + audio-driven lip sync with green boy face; QA में lip-sync, dialogue, pronunciations जांचें। Original voice WAV केवल tone/reference है, automatically variable script नहीं बोलता।
6. Opening original clips और 5 composited product segments और `09_premium_girl_cta.mp4` क्रम से merge करें। Original CTA audio/animation unchanged रखें।
7. QR generated frame को हर frame में actual official Google Play URL से बनाए static overlay के रूप में लगाएँ; AI generated QR पर भरोसा न करें; multiple timestamps scan-test करें।
8. Final QA: voice consistency, human lip-sync, exact Top5 ranking, all ≤ budget, no missing images, live price provenance, app QR URL, no duplicate characters, duration, rights; फिर ही publish करें।

## GitHub target
Repository: `jayantjos/trustfolio-animated-video-ads`
Suggested new folder: `masters/washing-machines/final-kit/` for README/config/scripts and `assets/video/washing-machines/final-kit/` for actual media. GitHub browser upload 25MB/file limit. Unpack ZIP and upload files into their folders; GitHub does NOT unzip uploaded archives. Put source videos in a release asset or Git LFS if repo growth is excessive.

## Status
This is a **verified asset + voice-reference preparation kit**, not a fully working live-price/TTS/lip-sync automation. Do not enable ad publishing until end-to-end QA passes.
