# StudentEnv — How to Use

`StudentEnv` simulates a student's psychological state over a 30-day period. Each step represents one day. The environment is a black box: you provide actions, it returns observations and a reward. You don't need to know what's inside.

---

## Setup

```python
from student_env import StudentEnv  # or copy the class directly

env = StudentEnv()
```

Optionally pass a fixed personality profile. If you don't, one is randomized for you:

```python
env = StudentEnv(traits={
    'openness': 0.6,
    'conscientiousness': 0.8,
    'extraversion': 0.3,
    'agreeableness': 0.5,
    'neuroticism': 0.4
})
```

---

## The loop

```python
obs, _ = env.reset()

for step in range(30):
    action = env.action_space.sample()  ## random action for now
    obs, reward, terminated, truncated, _ = env.step(action)

    if terminated or truncated:
        break
```

---

## Observations

`obs` is a numpy array of 5 floats, all between 0 and 1:

| Index | Variable | What it represents |
|-------|----------|--------------------|
| 0 | `energy` | How much the student has left in the tank |
| 1 | `stress` | Current pressure level |
| 2 | `self_efficacy` | How capable they feel |
| 3 | `social_need` | How much they need social contact |
| 4 | `days_until_deadline` | Normalized urgency signal (resets every 10 days) |

```python
energy, stress, self_efficacy, social_need, deadline_norm = obs
```

---

## Actions

The action space is `Discrete(6)`. Pass an integer 0–5:

| Integer | Action |
|---------|--------|
| 0 | Study |
| 1 | Attend lecture |
| 2 | Leisure |
| 3 | Socialize |
| 4 | Rest |
| 5 | Skip / do nothing |

```python
ACTION_NAMES = ["study", "attend lecture", "leisure", "socialize", "rest", "skip"]
action = 0  # study
obs, reward, terminated, truncated, _ = env.step(action)
```

---

## Reward

`reward` is a single float returned each step. Higher is better. Use it to evaluate or train your policy — you don't need to define it yourself.

---

## Generating a journal entry

After each step you have everything needed to prompt an LLM:

```python
ACTION_NAMES = ["study", "attend lecture", "leisure", "socialize", "rest", "skip"]

obs, _ = env.reset()
for day in range(30):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, _ = env.step(action)

    energy, stress, self_efficacy, social_need, deadline_norm = obs
    action_name = ACTION_NAMES[action]

    prompt = f"""Write a short diary entry for a student who {action_name}d today.
Energy: {energy:.2f}, Stress: {stress:.2f}, Self-efficacy: {self_efficacy:.2f}
3-5 sentences, first person, honest tone."""

    # send prompt to your LLM here
```

---

## Notes

- An episode is 30 days (`truncated=True` at day 30, `terminated` is never True)
- `reset()` re-randomizes the personality unless you passed fixed traits to `__init__`
- State is continuous and clipped to [0, 1] — no discrete buckets
