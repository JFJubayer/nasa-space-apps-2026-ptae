# 🎬 PTAE — "240 Seconds of Glory" Video Script
**Challenge:** Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars — NASA Space Apps Challenge 2026
**Project:** PTAE (Planetary Terrestrial Analog Engine)
**Total runtime:** 4:00 (240s) local-judging cut, + 0:30 global-nominee cut at the end

> Fill in `[Team Name]` / `[Speaker]` placeholders before recording. Existing audio/video assets have not been regenerated for this revised script; re-record/render and verify synchronization before submission. The standalone subtitle timestamps and line counts are unchanged.

> 🎙️ **AI scratch-track available:** [docs/voiceover/](voiceover/) has a synthesized narration of this script (`en-US-AvaNeural`) — files are named by their position on the 240s timeline: `000s-060s_who.mp3`, `060s-120s_why.mp3`, `120s-180s_what.mp3`, `180s-240s_how.mp3`, plus `000s-240s_full.mp3` (combined, ~3:23) and `240s-270s_bonus.mp3` (the 30s global-nominee cut). Use it as a scratch track for editing timing, or as a placeholder if a human narrator isn't available — swap in your own voice for the final cut where you can.

> 🎬 **Assembled rough-cut video available:** [docs/video/PTAE_240s_Video.mp4](video/PTAE_240s_Video.mp4) (~3:21) and [docs/video/PTAE_Bonus_30s.mp4](video/PTAE_Bonus_30s.mp4) are AI-assembled placeholders — title cards, real terminal output, real dashboard screenshots, and the real result plots, synced to the voiceover above. Subtitled versions with word-accurate burned-in captions are also included: `PTAE_240s_Video_Subtitled.mp4` / `PTAE_Bonus_30s_Subtitled.mp4`, plus standalone `.srt` files if you'd rather load captions in your editor. There's no on-camera host segment (that needs you filming yourself) — use this as a storyboard/animatic to guide your real edit, or as a fallback if you're short on time.

---

## Before you hit record

1. Use the checked-in 20-site real-data rankings for filming without regenerating data. If a separate five-site synthetic illustration is needed, follow README's isolated `data_synthetic_demo/` and `results_synthetic_demo/` commands; never export synthetic results into the dashboard.
2. Start the dashboard from its directory with `cd dashboard && python -m http.server 8000`, then open `http://localhost:8000`. Show its current JSON-backed leaderboard and radar chart for Section 3; do not substitute older generated plots without verifying their dataset and scope.
3. Have one slide ready: the mermaid architecture diagram from [README.md](../README.md) (Data Sources → Processing Engine → Deliverables), exported as an image.
4. Record screen at 1080p/60fps; record voiceover separately if possible for cleaner audio (or start from the AI scratch-track above).

| Time | Section | Beat |
|---|---|---|
| 0:00–1:00 | **WHO — Attention & Authenticity** | Hook + team |
| 1:00–2:00 | **WHY — Empathy for the Problem** | The gap PTAE closes |
| 2:00–3:00 | **WHAT — The Big Idea (Live Demo)** | Show it actually working |
| 3:00–4:00 | **HOW — Impact & What's Next** | Roadmap + close |
| 4:00–4:30 | *(bonus)* | 30-second global-nominee cut |

---

## 0:00–1:00 — WHO: Attention & Authenticity

**[VISUAL]** Cold open on the Moon/Mars analog challenge graphic, then hard cut to speaker on camera.

> **[SPEAKER, on camera, high energy]**
> "Before an astronaut ever sets foot on the Lunar South Pole, or a rover cracks Martian soil, every habitat, every rover wheel, every spacesuit joint has to survive a brutal dress rehearsal — on Earth. We're **[Team Name]**, and for the 2026 NASA Space Apps Challenge, we asked one question: *how does NASA actually know an Earth test site behaves like the Moon or Mars?*
>
> Today, that answer is mostly a guess — 'it's a desert, so it's basically Mars.' We built something that replaces the guess with a number."

**[VISUAL]** Title card wipes in: **PTAE — Planetary Terrestrial Analog Engine**, subtitle "Quantitative Earth Analogs for Moon & Mars Base Locations."

*(~110 words — leaves headroom for the title-card beat.)*

---

## 1:00–2:00 — WHY: Create Empathy for the Problem

**[VISUAL]** Split screen: real photos of Devon Island / Atacama / Iceland analog missions on the left, a big red question mark over a map on the right.

> **[SPEAKER, voiceover over B-roll]**
> "Mission planners already know a handful of famous analog sites — Devon Island, the Atacama Desert, Hawaii's lava fields. But those were chosen decades ago by intuition, not measurement. As Artemis and Mars missions get more ambitious, that's not good enough anymore.
>
> A lunar south-pole lander needs terrain with the *right slope distribution* for a safe touchdown. A Mars rover needs the *right ruggedness* so its wheels don't get trapped. Pick the wrong analog, and you find out your equipment fails only after it's already on another world — when it's too late and too expensive to fix.
>
> The real problem isn't a lack of candidate sites on Earth. It's the lack of a quantitative, repeatable way to score them against the Moon and Mars terrain data we already have."

**[TEXT OVERLAY]** "0 standardized way to *score* an analog site — until now."

*(~140 words.)*

---

## 2:00–3:00 — WHAT: Your Big Idea (Live Demo)

**[VISUAL]** Cut to full-screen dashboard rankings.

> **[SPEAKER, voiceover over live screen capture]**
> "So we built PTAE. Point it at a target — the lunar south pole region, or Jezero Crater on Mars — and it does the science for you."

**[SCREEN ACTION]** Open the checked-in Moon ranking in the dashboard; do not regenerate data during filming.
**[SPEAKER continues as the ranking loads]**
> "Current results compare 20 real Earth DEMs from AWS Terrain Tiles with LOLA for the lunar target and MOLA for the Martian target. Our **Analog Compatibility Index** compares terrain statistics. The synthetic demo is a separate five-site illustration."

**[VISUAL]** Highlight the checked-in Moon leaderboard in the dashboard:
```
#1  Teide / Tenerife Volcanic Field  87.22%
#2  Mount Etna                      86.79%
```
> "For the current lunar south-pole target, Teide leads the 20-site ranking at 87.22%; Mount Etna follows at 86.79%. These are terrain-statistics similarities, not proof of mission suitability."

**[SCREEN ACTION]** Switch to the checked-in Mars ranking in the dashboard.
> "For the current Jezero target, Kilauea leads at 55.84%, with Craters of the Moon second at 54.99%."

**[VISUAL]** Cut to `dashboard/index.html` — click between Moon/Mars toggle, click a marker to show the radar chart animating live.
> "A separate historical five-site study used real LOLA and Askja plus four synthetic Earth candidates; its leader changed across 5, 10, and 15 km windows. The new all-real crop study uses existing windows only. Mars and Earth still differ in resolution and physical footprint."

*(Recheck narration timing against the unchanged subtitle timestamps before recording.)*

---

## 3:00–4:00 — HOW: Impact & Your Needs

**[VISUAL]** Speaker back on camera, architecture diagram slide behind/beside them.

> **[SPEAKER, on camera]**
> "Current results use 20 real Earth DEMs from AWS Terrain Tiles, with LOLA and MOLA target DEMs for Moon and Mars. The prepared arrays and JSON rankings are already included. A separate five-site synthetic illustration provides a self-contained example, not the current dashboard rankings. These terrain similarities do not prove mission suitability.
>
> That's our next step: connect PTAE to Google Earth Engine for a continuous global scan, and layer in mineralogy from CRISM and ASTER so we're matching chemistry, not just terrain shape.
>
> Our ask is simple — mission planners and analog-site researchers, give us your candidate sites and your target metrics, and PTAE will tell you, with a number, how good a match you've really found. Because the next crew that walks on the Moon deserves to have trained on the *right* ground first.
>
> We're **[Team Name]** — thank you."

**[VISUAL]** End card: project name, GitHub link, team names, NASA Space Apps 2026 logo.

*(Recheck the revised narration's timing before recording.)*

---

## 4:00–4:30 — Bonus: 30-Second Global-Nominee Cut

*(Use only if selected as a global nominee — trim to picture-locked essentials.)*

> **[SPEAKER]**
> "Before astronauts travel to the lunar south pole region or Mars, their gear is tested on Earth. PTAE compares 20 real Earth DEMs from AWS Terrain Tiles with LOLA and MOLA targets. The synthetic demo is a separate five-site illustration. Teide leads the Moon ranking at 87.22%; Kilauea leads Mars at 55.84%. Different DEM scales make these indicative terrain similarities, not proof of mission suitability."

*(Recheck the revised narration against the unchanged 30-second subtitle timing.)*

---

## Delivery notes

- **Pacing:** ~130–150 words/minute of actual speech per section leaves 10–15s of visual-only beats (title cards, B-roll, dashboard clicks) in every minute — don't try to fill all 60s with talking.
- **Authenticity beat (first 15s):** the rubric explicitly rewards hooking the viewer in the first 15 seconds — the cold-open question ("how does NASA actually know...") is designed for that.
- **Show, don't just tell:** the WHAT section is scripted around commands that were run and verified against this repo (see [README.md](../README.md) Key Findings and [NASA_SPACE_APPS_SUBMISSION.md](../NASA_SPACE_APPS_SUBMISSION.md)) — don't substitute other numbers without re-running `main.py`.
- **Consistency:** if you regenerate data (`rm -rf data results && python main.py ...`) before filming, re-check the printed leaderboard still matches the numbers quoted above — seeds are fixed, so it will, but always confirm on your recording machine before rolling.
