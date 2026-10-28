# V12 — Fix remaining Hindi glyph boxes and make Green Boy talk without redoing whole Flow cartoon

**User-approved baseline:** V11 90-second Warm Gold washing-machine cartoon.
Review-only corrected V12 file was rendered locally from the actual uploaded V11 MP4; the V12 binary has **NOT** been uploaded to GitHub by this text-only connector.

## Visual QA (do not alter the other scenes)

- The FIVE `WHY THIS PICK?` Hindi captions were re-typeset with **Noto Sans Devanagari Bold** instead of letting an unsupported fallback font render a box/missing glyph. Zero U+25A1/U+FFFD/replacement characters in source subtitles.
- Source V11 and local output have the EXACT same compressed audio SHA256: `3d8f65abb3de5823e54f8a8a671a9279d535a4a480b4eb1bb4ae1037d826161d`.
- Local V12 SHA256 `056041708fec0169c0ba0a6282042e84e8888273c44d558412f2e95339512a0f`; 90.00 s, H264/AAC, 720×1280. Product graphic is a review of 28 Oct 2026 prices, NOT a live certified ad.
- Intro, four fixed specifications, background, portraits, product ranks, comparison, and CTA `https://trustfolio.in` remain unchanged.
- One user-reported box has not been precisely localized from supplied evidence; don't falsely claim every possible box is fixed. Ask for a timestamp/screenshot if still visible.

## Real technical solution for one Green Boy with changing product speech

Google Flow can produce the boy talking using **Omni Flash → Video → Ingredients**, with Green Boy's own photo as an ingredient. Current Google Flow Help also documents **Voices / reusable voice references and custom voices**, which helps the same sounding speaker appear in multiple generations.
Official help: https://support.google.com/flow/answer/16353334

But generating new brand names, prices and four specification facts for every budget **cannot be achieved by reusing an unchanged prerecorded talking mouth**. Reusing original generic Flow speaking footage with arbitrarily changing speech will NOT have accurate lip sync.

Recommended reliable low-credit contract:

1. ONE Flow generation: original exact Green Boy (green hoodie, large round glasses) in exact warm golden laundry-room, 4-6 second **timeless** Hindi introduction. Use a user-owned voice reference when permitted, audition and lock consistent voice identity. Record no brand, price or specification in this fixed script.
2. Each campaign: get backend-authoritative ranked Top5, then check exactly those five live-price IDs, stock, brand/product photo, and four actual source specs. Wrong photo or source missing → SKIP.
3. Dynamically generate 5 source-backed Hindi scripts/short normal-speed audio clips using ONE approved reproducible model/voice ID. Voice changes **words**, not timbre; save exact model ID and voice receipt source hash.
4. Show the appliance close-ups/screens during changing spoken facts, with Green Boy optionally pointing silently. This is legitimate voiceover, not a false claim his visible mouth matches the changing audio.
5. If user insists Green Boy visibly says new product-specific lines, run audio-driven mouth animation/lip sync on only five 8-10s Green Boy inserts **per campaign**; QA character consistency, mouth/audio timing, original background and no generated text. This is a potentially paid optional step.
6. Mix new clean Hindi audio only over 32–82 s; preserve original cartoon sound over 0–28 and 86–90 s. No robotic eSpeak, no synthetic speedup. Verify audible pronunciation.
7. Render specs, live price and correct photo independently. Before any Instagram/Facebook Reel publishing, verify new current live-price receipt again; if changed, re-render or SKIP.

### Reusable Flow prompt

“Use the supplied original Green Boy as exact identity reference. Keep the same large round glasses, green hoodie, face, hair, child age, warm cream-and-champagne laundry-room background and original cinematic 3D-cartoon aesthetic. Speaking shot: boy looks at camera, points warmly to the right, blinks and says in natural Indian Hindi ‘अब देखते हैं इस बजट के पाँच विकल्प। इनकी खूबियाँ एक-एक करके समझते हैं!’ Match lips to the exact Hindi words. Do not generate any model, price, floating card, writing, logo, music, extra character, different outfit or revised background. Fixed single shot only, 9:16 portrait. If supported use the same reviewed character voice reference.”

Flow speech/audio generation is experimental and the voice may vary; do not assume perfect preservation of the original actor.
Google official overview: https://blog.google/innovation-and-ai/models-and-research/google-labs/flow-adds-speech-expands/

## Safety / active system

This is a source-control STRATEGY DOCUMENT only: it creates NO new social schedule, Google Flow run, billable API request, Meta post, audio recording or additional cartoon asset. Existing `v10_fixed_voice.py` is a separate proposed speech source and is not yet approved as same Flow character. A fully automated talking-mouth version requires a dedicated lip-sync implementation plus first video QA. Keep existing poster automation untouched.
