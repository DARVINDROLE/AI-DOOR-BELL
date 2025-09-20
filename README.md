# AI-DOOR-BELL

 ┌──────────────────────┐
 │ Visitor arrives      │
 │ (motion/person)      │
 └─────────┬────────────┘
           │
           ▼
 ┌──────────────────────┐
 │ Raspberry Pi detects │
 │ person (camera+AI)   │
 └─────────┬────────────┘
           │
           ▼
 ┌─────────────────────────┐
 │ Capture snapshot/video   │
 │ + event metadata         │
 └─────────┬────────────────┘
           │
           ▼
 ┌──────────────────────┐
 │ Send event to        │
 │ Backend API           │
 └─────────┬────────────┘
           │
           ▼
 ┌───────────────────────────┐
 │ Backend stores event       │
 │ + AI generates:            │
 │  • Visitor summary         │
 │  • Suggested replies       │
 └─────────┬─────────────────┘
           │
           ▼
 ┌───────────────────────────┐
 │ Owner Mobile App receives │
 │ notification + summary     │
 │ (via WebSocket/Push)       │
 └─────────┬─────────────────┘
           │
           ▼
 ┌───────────────────────────┐
 │ Owner interacts:           │
 │  • Chooses AI suggestion   │
 │  • Or types own reply      │
 └─────────┬─────────────────┘
           │
           ▼
 ┌───────────────────────────┐
 │ Reply sent to Backend     │
 │ → routed to Raspberry Pi   │
 │ (MQTT/WebSocket)           │
 └─────────┬─────────────────┘
           │
           ▼
 ┌───────────────────────────┐
 │ Raspberry Pi displays text │
 │ on screen + speaks reply   │
 │ via TTS to visitor         │
 └─────────┬─────────────────┘
           │
           ▼
 ┌──────────────────────┐
 │ Interaction complete │
 │ (event logged)       │
 └──────────────────────┘
