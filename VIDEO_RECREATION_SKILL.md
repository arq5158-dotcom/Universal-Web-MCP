# Video Recreation Skill: Study Any Video, Rebuild It With Our Character 🎬🔍

> **Skill Purpose:** You receive a source video of any type (DIY build, renovation, life hack, story, ASMR) and return a copy-paste prompt kit that recreates it in Google Flow with the user's own character (Lia, Ava, Blue, Ashzo or whoever they attach). Study the video in depth before writing a single prompt: the kit is only as good as your understanding of every shot, sound and object. This file is the exact process that worked, including the mistakes that cost generations and how they were fixed.

**Output:** one page (artifact/HTML) with a copy button on every prompt, containing:

1. A short source breakdown: what happens, how long, dialogue, sound.
2. A timeline that maps each part of the source to a clip.
3. Image prompts: a first frame for clip 1 and every new location, and a last frame for every clip.
4. One video prompt per clip, each stating its own length.
5. How to run it: settings, what to attach, the order.
6. Check-before-stitch notes, CapCut edit notes and a post caption with hashtags.

**Model:** Gemini Omni Flash 1.1 in Google Flow, 9:16, 720p, clip lengths 4, 6, 8 or 10 seconds (Frames to Video with first and last frame, Ingredients, Video-to-Video up to 10s). Veo 3.1 stops at 8 seconds. Check https://support.google.com/flow/answer/16352836 when unsure, because features change.

```
 1 Intake ──▶ 2 Map the video ──▶ 3 Zoom in ──▶ 4 Study sound
                                                     │
 User generates ◀── 7 Deliver page ◀── 6 Write kit ◀─ 5 Story map
      │   ▲
      ▼   └──── regenerate (same frames) ────┐
  Clip right? ── no ──▶ 8 Fix the words in EVERY prompt
      │ yes
      ▼
  Stitch in CapCut
```
Steps 1–7 happen once per video. Step 8 repeats for every clip that comes back wrong.

---

## Step 1: Intake

Start working in your first reply; don't ask questions the video can answer.

1. Copy the upload into a scratch folder as `src.mp4` and work only on the copy.
2. Read its properties: duration, resolution, frame rate, frame count and whether it has audio.
3. Re-read the user's standing rules (below) and any notes they sent with the video.
4. Note what they asked for in this message: hyperlapse, normal speed, more hooking, a specific length.

```bash
mkdir -p vid && cp "<upload path>" vid/src.mp4
ffprobe -v error -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames,sample_rate,channels \
  -of default=nw=1 vid/src.mp4
```

**The user's standing rules:**

- Never describe the character's looks. Write "the attached character, exactly as the reference"; the user attaches the image to every generation. Describe a character in words only for a text-only model.
- Keep the established workflow: a first frame for clip 1 (and each new location), a last frame for every clip, and each clip starting from the previous clip's last frame. Don't invent new prompt strategies.
- Make every prompt fully copy-paste ready, with its duration, what to attach and the settings stated.
- Keep each action in its own clip or segment. Omni Flash makes mistakes when one prompt has several tasks.
- Target 30–40 seconds in total; go to 60 only when the process can't be shown in less.
- No voiceover or music inside clips. Sound is foley only; music and the ElevenLabs voiceover are added later in CapCut.
- No text, captions or logos in the video.
- No faces, names or places that look like celebrities, royalty or famous locations: Flow refuses those. No killing or crime scenes.

## Step 2: Map the whole video

Before any detail work, get the full story in view: where the cuts are and what happens every second.

1. Run scene-cut detection twice (thresholds 0.25 and 0.22) and list the cut times.
2. Extract one frame per second with the timestamp burned in, then tile them into contact sheets of 24 frames (6×4), so one sheet covers 24 seconds. A 2-minute video is 5 sheets.
3. Look at every sheet, in order. Never skip one.
4. While looking, keep a running log, one line per shot: start time, shot type (wide, close-up, overhead), camera (static, push-in, pan, handheld), who is in frame and what changes.

```bash
cd vid
ffmpeg -hide_banner -i src.mp4 -vf "select='gt(scene,0.25)',showinfo" -an -f null - 2>&1 \
  | grep -o "pts_time:[0-9.]*" | sed 's/pts_time://' | awk '{printf "%.2f ", $1}'
mkdir -p f1 && ffmpeg -loglevel error -i src.mp4 \
  -vf "fps=1,scale=192:-1,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6" f1/%03d.png
for i in 0 1 2 3 4; do s=$((i*24+1)); ffmpeg -loglevel error -y -start_number $s -i f1/%03d.png \
  -frames:v 1 -vf "tile=6x4:padding=4:margin=4" sheet_$i.png; done
```

Two cautions from experience:

- Scene detection is a hint, not the truth. Timelapse and hyperlapse footage triggers many false cuts, and very fast cuts are missed. Trust your eyes on the sheets.
- One frame per second misses cuts shorter than a second. If two neighbouring frames look unrelated, zoom in there (Step 3).

## Step 3: Zoom in on the hook, the ending and anything unclear

The first seconds decide whether people keep watching, and the ending decides whether they share. Study both at higher density.

1. Extract the first 12 seconds and the last 10 seconds at 2 fps (4–8 fps for fast cuts), with timestamps, and tile them into sheets.
2. For any moment you can't read, pull single full-size frames. Put the same object at different times side by side to check its shape, colour and count.
3. Write down the details a prompt needs: every person and their role, each prop with material, size and count, where things stand, camera height and angle, lens feel, light, weather and time of day.
4. Note continuity errors in the source, such as a tool, a fire or an accessory that appears with no action causing it. Your kit adds the missing action (a lighter before the fire) so the model doesn't invent one.

```bash
mkdir -p f4
ffmpeg -loglevel error -y -ss 0 -t 12 -i src.mp4 \
  -vf "fps=2,scale=192:-1,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=14:fontcolor=yellow:box=1:boxcolor=black@0.6" f4/a%03d.png
ffmpeg -loglevel error -y -i f4/a%03d.png -frames:v 1 -vf "tile=6x4:padding=4:margin=4" hook.png
# ending: change -ss to (duration - 10) and tile 6x2 into end.png
# one full frame:  ffmpeg -ss 37.5 -i src.mp4 -frames:v 1 detail.png
# side by side:    ffmpeg -i a.png -i b.png -filter_complex hstack cmp.png
```

## Step 4: Study the sound

Work out three things: where people speak, whether there is music, and which foley sounds carry each beat.

1. Draw a spectrogram of the whole track and look at it. Speech shows as stacked bands in the 100–4000 Hz range, music as steady horizontal lines, foley as short bursts.
2. Print loudness per second to find quiet parts, drops and hits.
3. Check for speech. Use a transcriber such as Whisper if one is installed. If not, crop and read the burned-in captions, and say in the kit that dialogue lines are your best reading.
4. Write a sound line for each beat: the dialogue with its seconds, plus the foley.

In the pool video, the only dialogue was in the first 7 seconds. After that came sped-up building sounds with no music. That meant two normal-speed dialogue clips, then foley-only hyperlapse clips.

```bash
ffmpeg -loglevel error -y -i src.mp4 -lavfi "showspectrumpic=s=1200x400:legend=0:color=intensity:scale=log" spec.png
ffmpeg -hide_banner -i src.mp4 -af "astats=metadata=1:reset=44100,ametadata=print:key=lavfi.astats.Overall.RMS_level" \
  -f null - 2>&1 | grep RMS_level | awk -F= 'NR%3==1{printf "%s ", int($2)}'
ffmpeg -i src.mp4 -af silencedetect=n=-40dB:d=0.3 -f null - 2>&1 | grep silence_
python3 -c "import whisper" 2>&1 | head -1   # is a transcriber available?
```

## Step 5: Write the story map and decide the clips

Turn your shot log into beats, then the beats into clips. Every choice here prevents a failure later.

1. **Assign roles.** The user's character takes the main or helper role; other people stay as in the source (an old woman stays an old woman). Make sure no one looks like a real famous person.
2. **Put the hook first.** The first 1–3 seconds show the most emotional or surprising moment: someone suffering, a reveal, a big machine, the finished payoff.
3. **Cut what doesn't move the story,** such as walking up steps, repeated passes or waiting. Aim for 30–40 seconds after the edit.
4. **One action per clip,** with lengths of 4, 6, 8 or 10 seconds. Give hard actions shorter clips.
5. **Decide the speed of each clip:** normal speed for dialogue and emotion, fast-forward hyperlapse for long build work.
6. **Mark each new location.** A clip that opens a new place (a hard cut in the source) needs its own first-frame image; every other clip starts from the previous clip's last frame.
7. **Fix realism:** a helper for very heavy lifting, a visible cause for fire and light, nothing appearing from nowhere.

The pool video (2 minutes) became 11 clips, 80 seconds raw, about a minute after the edit:

| Clip | Beat | Speed | Length |
| --- | --- | --- | --- |
| 1 | Hook: an old woman lives in an abandoned pool; Lia offers help | Normal, dialogue | 6s |
| 2 | "Wait here, you'll have a new home" in a tent | Normal, dialogue | 4s |
| 3 | Clean out the pool and pressure-wash it | Hyperlapse | 8s |
| 4 | Line and frame the hidden room | Hyperlapse | 8s |
| 5 | Cover the pool and bury it under soil | Hyperlapse | 8s |
| 6 | Frame an octagonal cabin on top | Hyperlapse | 8s |
| 7 | Thatch the roof | Hyperlapse | 8s |
| 8 | Walls, windows, door and paint | Hyperlapse | 8s |
| 9 | Cabin interior and the trapdoor | Hyperlapse | 8s |
| 10 | The hidden room comes alive | Hyperlapse | 8s |
| 11 | Walking her home | Normal | 6s |

Put this table at the top of the kit, with the source time range of each beat, so the user sees exactly what became what.

## Step 6: Write the kit

### Image prompts (first and last frames)

Omni Flash makes far fewer mistakes when it has a start and an end frame, so image prompts come first.

- **First frame** (clip 1 and every new location): describe the whole set as a photo. Give the camera position, the place, every object with its material, colour, size and count, other people, the light, and where the character stands and what she's doing.
- **Last frame** (every clip): start with "Exact same framing as the start frame", repeat the key set details, then state only what has changed.
- Each image names what to attach: the character image, plus the previous image when it's a last frame. That keeps the camera and set locked.
- End every image prompt with: no text, no logos, no tripod or phone visible, and the person does not resemble any celebrity.

Example last frame from the pool kit:

```
Exact same framing as the start frame, same abandoned pool, tarp shelter, leaves and trash. The attached character now stands beside the shelter helping the elderly woman to her feet, one arm around her shoulders, the woman leaning on her. Neither of them looks at the camera. Vertical 9:16 realistic iPhone photo. No text, no logos, no tripod or phone visible.
```

### Video prompts

Every video prompt uses the same labelled blocks, in this order:

| Block | What goes in it |
| --- | --- |
| FORMAT | 9:16, 720p, the clip's length, the speed (normal or fast-forward), one shot or cuts, locked or moving camera, realistic iPhone look |
| CHARACTER | "the attached character, exactly as the reference", plus anyone else; how many of her; never looks at the camera |
| SCENE | The place, light and weather, with anything that must not change |
| OBJECT | The one thing being built or changed, with the shape and size it keeps |
| ACTION | Timed segments (0–2s, 2–4s …): what she does, named as her action, ending on the end frame |
| CAMERA | Position, height and angle; "completely static" when it doesn't move; "ending exactly on the end frame" |
| SOUND | Foley for each segment, dialogue in quotes with its seconds, "No music" |
| NEGATIVES | The failures to prevent: clones, things moving by themselves, light changes, camera drift, text, extra people, looking at the camera |

Normal-speed example (pool kit, clip 1):

```
FORMAT: 9:16 vertical, 720p, 6 seconds, normal real-time speed, one continuous shot, locked-off camera, realistic iPhone footage.
CHARACTER: the attached character, exactly as the reference, and the same elderly woman as in the start frame. Neither of them ever looks at the camera.
SCENE: an abandoned empty outdoor swimming pool with rust-stained light-blue tiles, dead leaves and trash on the floor and a torn tarp shelter in the deep end, with a snowy bare forest around it. Overcast winter light.
ACTION: 0–4s: the attached character asks gently, "Do you live here?" The old woman answers quietly, "Yes… my home is gone." The attached character says, "I'll help you." 4–6s: she helps the old woman to her feet and puts an arm around her shoulders.
CAMERA: completely static, high angle from above the pool steps looking down the length of the pool, ending exactly on the end frame.
SOUND: cold wind, a few distant crows, rustling leaves, their two voices. No music.
NEGATIVES: no timelapse, no fast motion. The pool, shelter and trash stay exactly the same. No extra people, no text or subtitles, no logos, no tripod or phone visible, no looking at the camera.
```

Hyperlapse example (pool kit, clip 5, after the fix in Step 8):

```
FORMAT: 9:16 vertical, 720p, 8 seconds, FAST-FORWARD TIMELAPSE at about 30x speed: a full day of her work squeezed into 8 seconds. She works fast and nonstop from the very first frame; only the last second plays at real speed. One continuous shot with no cuts, locked-off camera, realistic iPhone footage.
CHARACTER: the attached character, exactly as the reference, and only one of her in the frame at all times. She does every bit of the work herself, moving fast with motion blur on her arms and legs, rushing straight from one task to the next. She never stands still before the last second and never looks at the camera.
SCENE: the framed pool seen from above, with the snowy forest around it. The sky stays the same flat overcast gray and the light never changes.
OBJECT: the pool's rectangle, with one square hatch opening in its middle. The steps at the bottom of the frame stay exactly as they are.
ACTION (bury the pool): 0–3s: she carries plywood sheets one at a time, lays each one across the ceiling joists and nails it down, until the pool is closed in except for one square hatch opening in the middle. 3–7s: she pushes a wheelbarrow of soil back and forth, tips it onto the plywood and rakes it flat until the soil is level with the deck. 7–8s, real speed: she stops beside the wheelbarrow and stands still.
CAMERA: completely static, same high angle from above the pool steps. It never moves, tilts or zooms; the trees stay in exactly the same place in every frame. Settling on the end frame.
SOUND: sped-up plywood thuds, nail gun bursts, soil pouring, wheelbarrow rattling. No music, no speech.
NEGATIVES: She never stands still before the last second. Exactly one of her, no duplicates. Nothing moves or appears by itself; every piece moves only in her hands. The sky, light and weather never change. No jump cuts, no camera movement, no slow motion. The hatch stays open and square in the middle. No extra people, no text, no logos, no tripod or phone visible, no looking at the camera.
```

## Step 7: Deliver the kit

Deliver one page the user can work from on their phone, with a copy button on every prompt. Put the sections in this order:

1. **Title and one-paragraph summary** of the source: length, what happens, dialogue, sound.
2. **The clip timeline table** from Step 5, with source times.
3. **How to run it:**
    1. Generate the images first, in order (Image mode, 9:16), attaching the character image plus the image listed on each prompt.
    2. Generate each video with Omni Flash 1.1 in Frames mode at 9:16, 720p. The start frame is that clip's first frame, or the previous clip's last frame. The end frame is that clip's last-frame image.
    3. Join the clips in CapCut in order.
4. **One card per clip,** grouped by location. Each card shows the length, speed and dialogue tags, then the first-frame prompt (if any), the last-frame prompt and the video prompt. Each prompt lists what to attach.
5. **Check before you stitch:** what to look for in each result (her speed, one of her, sky locked, nothing moving by itself), plus "if a clip plays slow, speed it up 2× in CapCut instead of regenerating".
6. **Edit and post:** CapCut notes (trims, crossfades, where music goes, where the voiceover goes) and a post caption with about 7 hashtags. The caption's first line is a curiosity hook, such as "Wait for what's hidden under the floor".

In the chat reply, keep it short: what the source does, how many clips and seconds, anything you changed from the source and why, and one tip. Don't paste the whole kit into chat.

When the user later asks for a change, edit the same page and say what changed. Don't start a new kit.

## Step 8: When a generated clip comes out wrong

When the user sends back a bad result, study it like a source video before touching the prompt. Don't guess from their description alone.

1. Extract the generated clip at 3 fps with timestamps and tile it into one sheet.
2. Read your prompt line by line against the frames and list each failure with the second it happens.
3. For each failure, find the words in your prompt that invited it. The cause is usually your wording, not the model.
4. Rewrite every prompt that uses those words, not only the failed clip. The same words will fail again in the other clips.
5. Keep the image prompts and frames the same when you can, so the user can regenerate with the frames they already made.
6. Reply with what went wrong in plain words, what changed, and the fixed prompt for that clip ready to paste. Update the kit page too.

```bash
mkdir -p gen && ffmpeg -loglevel error -y -i generated.mp4 \
  -vf "fps=3,scale=200:-1,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=14:fontcolor=yellow:box=1:boxcolor=black@0.6" gen/%03d.png
ffmpeg -loglevel error -y -i gen/%03d.png -frames:v 1 -vf "tile=6x4:padding=4:margin=4" gen/sheet.png
```

What happened with the pool kit, clip 5: Lia stood still while the plywood flew in by itself, the sky jumped to blue and back, and a second Lia appeared. All three came from the prompt's own words:

| What went wrong | Words that caused it | Fix |
| --- | --- | --- |
| She stood still; plywood moved by itself | Verbs on the objects: "planks race across the floor", "panels snap up" | Every step names her doing it: "she carries… lays… nails". NEGATIVES: "Nothing moves or appears by itself; every piece moves only in her hands." |
| A second Lia appeared | "a ghosted figure popping up in a new spot every half second" | "Only one of her in the frame at all times", working nonstop with motion blur, stopping only in the last second |
| The sky flashed blue and back | "Clouds race", "daylight flickers as hours pass" to show time passing | "The sky stays the same flat overcast gray and the light never changes" |
| The camera crept | Only "locked-off camera" | "It never moves, tilts or zooms; the trees stay in exactly the same place in every frame", plus "no jump cuts" |

## Lessons learned

Each row is a mistake that cost the user a generation. Write the fix into the prompt from the start.

| Problem | Cause | Fix |
| --- | --- | --- |
| Hyperlapse played at walking pace | The word "hyperlapse" on its own | FORMAT: "FAST-FORWARD TIMELAPSE at about 30x speed, only the last second at real speed". Give a progress checkpoint every 2 seconds (too much work to fit at normal pace). NEGATIVES: no slow motion, no real-time walking. Fallback: 2× speed in CapCut. |
| Steps skipped or merged | Several tasks in one prompt | One action per clip or per timed segment; shorter clips for hard actions |
| Clip came out 8 seconds instead of 10 | A Veo model or an 8s length setting; Flow remembers the last length used | Tell the user to set Gemini Omni Flash 1.1 and 10s before each generation |
| Hands and phone deformed in video-to-video | The model redraws hands it can't see clearly | Add: "two normal hands with five fingers each, the phone held naturally with fingers wrapped around its edges… no extra or missing fingers". If it still fails: "Keep the original poses, silhouettes, hands and phone from the input video; change only the person's identity, textures, skin, lighting and materials." |
| Different music in every clip | Music generated inside clips | Foley only, "No music" in SOUND; music goes in CapCut |
| Character looked into the lens | No instruction | "Never looks at the camera" in CHARACTER and NEGATIVES, unless the user asks for vlog-style talking to the lens |
| Garbled words on screen | Text requested or allowed in the clip | "No text, no subtitles, no logos"; captions are added in CapCut |
| Fire or an object appeared from nowhere | Copied a continuity error from the source | Add the missing action, such as she lights it with a lighter |
| One person lifting something huge looked fake | Copied the source literally | Add a helper with their face out of frame |
| Generation refused | A face, name or place resembling a celebrity, royalty or a famous location; a crime or killing scene | "An ordinary person who does not resemble any celebrity"; invented names and places; no violence |
| Characters and sets drifted across clips | Too many clips, or no frames | Fewer clips with quick jump cuts inside; first and last frames for every clip; every WIDE shot from the same camera position |
| The user was annoyed | A new prompt strategy replaced their workflow | Keep the established format (first frame, last frames, chaining) and improve the wording inside it |
| Slow start, viewers scroll away | Followed the source order | Hook in the first 1–3 seconds, cut walking and waiting, 30–40 seconds total |

One habit matters most: when something fails, find the exact words that caused it and remove them from every prompt, not just the clip that failed.

## Command cheat sheet

All study work needs only ffmpeg and ffprobe. Look at every image you make; a sheet you never open teaches you nothing.

| Job | Command |
| --- | --- |
| Properties | `ffprobe -v error -show_entries format=duration -show_entries stream=codec_type,width,height,r_frame_rate,nb_frames -of default=nw=1 src.mp4` |
| Scene cuts | `ffmpeg -i src.mp4 -vf "select='gt(scene,0.25)',showinfo" -an -f null - 2>&1 \| grep -o "pts_time:[0-9.]*"` |
| 1 fps frames with time | `ffmpeg -i src.mp4 -vf "fps=1,scale=192:-1,drawtext=text='%{pts\:hms}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6" f1/%03d.png` |
| Contact sheet (24 frames) | `ffmpeg -start_number 1 -i f1/%03d.png -frames:v 1 -vf "tile=6x4:padding=4:margin=4" sheet_0.png` |
| Dense sheet in one step | `ffmpeg -i src.mp4 -vf "fps=8,scale=180:-1,drawtext=text='%{pts\:flt}':x=3:y=3:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=12x10" -frames:v 1 dense.png` |
| One full frame | `ffmpeg -ss 37.5 -i src.mp4 -frames:v 1 detail.png` |
| Compare two frames | `ffmpeg -i a.png -i b.png -filter_complex hstack cmp.png` |
| Spectrogram | `ffmpeg -i src.mp4 -lavfi "showspectrumpic=s=1200x400:legend=0:scale=log" spec.png` |
| Loudness and silences | `ffmpeg -i src.mp4 -af volumedetect -vn -f null -` and `-af silencedetect=n=-40dB:d=0.3` |

## Final checklist before sending the kit

- [ ] Every sheet of the source was looked at, plus the hook and the ending at 2 fps or more.
- [ ] The hook lands in the first 1–3 seconds and the edited total is 30–40 seconds (60 only if needed).
- [ ] Each clip has one action, a length of 4, 6, 8 or 10 seconds written inside its FORMAT, and its speed stated.
- [ ] Clip 1 and each new location have a first frame; every clip has a last frame; each prompt says what to attach.
- [ ] The character is only "the attached character, exactly as the reference", never described.
- [ ] Every action names who does it; nothing moves by itself; "exactly one of her"; light and sky are locked.
- [ ] Hands are described as natural with five fingers wherever something is held.
- [ ] SOUND is foley only, with "No music"; no voiceover inside the clips.
- [ ] NEGATIVES cover text, logos, extra people, looking at the camera, camera drift and the clip's own risks.
- [ ] No celebrity likeness, famous place, or crime scene anywhere.
- [ ] The page works on a phone and every prompt has a copy button.
