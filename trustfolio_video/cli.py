"""CLI reports BLOCKED with source evidence instead of generating misleading ads."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from .contract import Blocked, campaign, fetch, validate
from .storyboard import build, validate_registry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--category', required=True)
    parser.add_argument('--budget', type=int, required=True)
    parser.add_argument('--mode', choices=['budget','brand_budget','comparison'], default='budget')
    parser.add_argument('--brand', default='')
    parser.add_argument('--output', required=True)
    parser.add_argument('--registry', default='config/worlds.json')
    parser.add_argument('--duration', type=int, choices=[15,20,30], default=20)
    args = parser.parse_args()
    dest = Path(args.output); dest.mkdir(parents=True, exist_ok=True)
    spec = campaign(args.category, args.budget, args.mode, args.brand)
    registry = json.loads(Path(args.registry).read_text())
    validate_registry(registry)
    world = next((w for w in registry['categories'] if w['slug'] == args.category and w['enabled']), None)
    report = {'checked_at':datetime.now(timezone.utc).isoformat(),'campaign':spec,'publishing_enabled':False}
    try:
        if world is None:
            raise Blocked('Category unsupported or disabled')
        snapshot = fetch(spec)
        (dest/'snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
        approved = validate(snapshot)
        storyboard = build(approved, world, duration=args.duration)
        (dest/'storyboard.json').write_text(json.dumps(storyboard, ensure_ascii=False, indent=2))
        report.update(status='DATA_APPROVED',render_status='NOT_RENDERED')
    except (Blocked, KeyError, TypeError, ValueError) as error:
        report.update(status='BLOCKED',reason=str(error),render_status='NOT_RENDERED')
    (dest/'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['status'] == 'DATA_APPROVED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
