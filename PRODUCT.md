# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Astro (static output) + Vue 3 islands only where interaction is needed. Editable content (texts, prices, photos, site state) lives in Astro content files under `src/content/` — no CMS. No hosting-provider integration; the client deploys the static build themselves. Confirmed on 2026-09-27.

## What it is

SUNNA is a semi-autonomous Pilates Reformer studio in Santa Cruz de Tenerife (C/ San Francisco Javier 5, bajo exterior, 38001 — final confirmation pending). Six reformers, one person per machine, guided video classes on an iPad at each reformer, bluetooth headphones at each reformer, access with the phone. No permanent instructor in the room. Recovery (infrared sauna and red light) is part of the opening.

## Who it is for

Someone who has never heard of SUNNA, usually arriving on a phone from Instagram. The model is new to almost everyone locally, so the site must explain it without making it seem complicated.

## The single job

Book the first session: a free 45-minute onboarding with the SUNNA team. It is the primary button everywhere and must always be at hand (fixed at the bottom on mobile). Everything else is secondary. Success = a first-time visitor understands how it works in 30 seconds and books.

## The single message

You train when you want, at your own pace, with a class guided on screen — and you never start alone: the first time, we show you everything.

## Two states

- **Pre-opening:** primary action becomes "Quiero ser socio/a fundador/a" (waitlist / founders form: name, email, phone, consent). Opening date shown once confirmed.
- **Open:** primary action returns to "Reserva tu primera sesión gratis", connected to bsport.
Switchable with one setting in the content files (no code change).

## Facts to preserve

- Classes: Full Body, Pierna, Brazo, Core, Movilidad, Estiramientos. Long 40–45 min, short 15–25, mobility 10–15. Languages: castellano, inglés, alemán, francés (largest catalog in English).
- Each booking is a 1-hour block: up to 50 min of class + time to enter, set up and leave.
- First 2–3 weeks: studio only opens with SUNNA staff inside (08:00–14:00 and 16:00–22:00). Then autonomous access, aiming for 05:00–23:00.
- Safety: only people with a booking can enter, cameras, help phone and WhatsApp.
- Minimum age to train alone: 18.
- Founding members: only 40 places; founder price protected forever while they stay subscribed (leaving and returning means current rate); opening booking priority; private opening event invite; recognition as founding member; early access to news, workshops and events; welcome pack (socks, tote bag, stickers and more).
- Memberships (provisional, to be confirmed): Basic 55 €/mes (4 sessions, 1 red light), Standard 100 € (8 sessions, 2 red light + 1 sauna), Pro 140 € (12 sessions, 3 red light + 2 sauna), Premium 180 € (unlimited subject to availability, "desde 3 € por sesión", unlimited recovery with booking + booking priority; highlighted).
- Not on the opening site: single class, bonos, recovery packs, tourist passes.
- The first session explains how things work and safe use of the machine. It is NOT a medical assessment and must never be presented as one. Recovery: no health promises.

## Open decisions (SUNNA to confirm)

Final prices and whether founder and standard prices differ; final address and opening date; booking/cancellation windows (bsport); cancellation notice (10 days) and membership pause; minimum accompanied age (14 or 16); what to bring; Instagram link, domain, WhatsApp number, help phone; final logo, palette and typefaces after the colour rebrand; real photos (site ships with marked photo slots).

## Voice

Close, short, no ad-speak. Short sentences, numbered steps, icons; no long paragraphs about the Pilates method. Inclusive Spanish ("sola/o", "socio/a fundador/a"); reword to neutral where the slash reads forced.

## Source of truth (client rule, 2026-09-27)

- **Content:** everything comes from the PDF brief (`Social-Media-Study-2026-ES.pdf`), using its own wording. Do not invent copy, claims or labels.
- **Visuals:** everything comes from the reference design `SUNNA Web.html` (layout, components, colours, type, motion). Its copy and prices are not content.

## Brand commitments

- Always use the original logo and symbol; never redraw or change proportions.
- Feel: contemporary, Mediterranean, warm and cared-for, with personality. Lots of light and air, real photos.
- Colour: neutral luminous base with one warm accent; soft, lively tones, never dark or muted. Materials: light wood, fabrics and curtains, warm indirect light, terracotta and olive details.
- Avoid: generic gym, clinic/physio, spiritual wellness, tech startup, cold luxury, stock photos with posing models, neon, challenge messaging, giveaways, invented figures ("800 classes"), a tech-jargon section.

## Technical constraints

- Bookings, payments and access live in bsport and Kisi; no custom systems. bsport integration deferred for now (placeholders). Kisi is only explained, not integrated.
- Four languages (added 2026-09-28): Spanish at `/`, English `/en/`, German `/de/`, French `/fr/`. Each has its own `src/content/<lang>/home.yaml`; settings (`es/ajustes.yaml`) are shared. Legal pages exist only in Spanish and are linked with an "(ES)" mark from the other languages. Visiting `/` redirects on the server (Caddy, `servidor/idioma.caddy`) by browser language (es/ca/gl/eu → Spanish, en/de/fr → theirs, anything else → English) unless the visitor picked a language in the switcher (cookie `sunna-idioma`); search engine bots are never redirected.
- Local SEO for "pilates reformer Santa Cruz de Tenerife": title, copy, Google Business link, map, LocalBusiness structured data.
- Legal: aviso legal, privacidad, cookies (real consent banner), condiciones de membresía.
- Analytics and Meta pixel only after consent.
- Floating WhatsApp button and Instagram link.
- Optimised photos, fast on mobile. Client must be able to edit texts, prices and photos without developers.
