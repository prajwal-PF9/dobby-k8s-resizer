from controller.cost_calculator import calculate_monthly_saving


def build_recommendation_blocks(recs, instance_type: str) -> list:
    """Build Slack blocks listing recommendations with cost savings."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":bulb: Resource Optimization Recommendations"},
        }
    ]

    for rec in recs:
        lines = [f"*Namespace:* `{rec.namespace}`  |  *Deployment:* `{rec.deployment}`"]
        total_saving = 0.0

        for c in rec.containers:
            saving = calculate_monthly_saving(
                current_cpu_m=c.current_cpu_m,
                rec_cpu_m=c.rec_cpu_m,
                current_mem_bytes=c.current_mem_bytes,
                rec_mem_bytes=c.rec_mem_bytes,
                instance_type=instance_type,
            )
            total_saving += saving

            cur_cpu = f"{int(c.current_cpu_m)}m"
            rec_cpu = f"{int(c.rec_cpu_m)}m"
            cur_mem = f"{c.current_mem_bytes // (1024**2)}Mi"
            rec_mem = f"{c.rec_mem_bytes // (1024**2)}Mi"

            lines.append(
                f"  • `{c.name}`: CPU {cur_cpu} → {rec_cpu} | Memory {cur_mem} → {rec_mem}"
            )

        lines.append(f"  :moneybag: Estimated saving: *${total_saving:.2f}/month*")
        lines.append("  Run `/resize apply` to apply all recommendations.")

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(lines)},
        })
        blocks.append({"type": "divider"})

    return blocks


def build_applied_blocks(applied: list) -> list:
    """Build Slack blocks confirming which Deployments were patched."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":white_check_mark: Resources Updated"},
        }
    ]

    for entry in applied:
        text = (
            f"*Namespace:* `{entry['namespace']}`  |  *Deployment:* `{entry['deployment']}`\n"
            f"  • `{entry['container']}`: CPU → `{entry['cpu']}` | Memory → `{entry['memory']}`"
        )
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})

    return blocks


def build_error_blocks(message: str) -> list:
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":x: *hack-resizer error:* {message}"},
        }
    ]


_SLACK_BLOCK_LIMIT = 48  # Slack hard limit is 50; keep a small buffer


def post_message(slack_client, channel: str, blocks: list) -> None:
    """Post blocks to Slack, splitting into multiple messages if over the 50-block limit."""
    if len(blocks) <= _SLACK_BLOCK_LIMIT:
        slack_client.chat_postMessage(channel=channel, blocks=blocks)
        return

    # Split into chunks, each chunk gets its own message
    for i in range(0, len(blocks), _SLACK_BLOCK_LIMIT):
        chunk = blocks[i:i + _SLACK_BLOCK_LIMIT]
        slack_client.chat_postMessage(channel=channel, blocks=chunk)
