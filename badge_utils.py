from datetime import datetime, timedelta
from models import Badge, Achievement, User, Team, team_members
from app import db_session
from sqlalchemy import select

# Define badge types
BADGES = {
    'team_creator': {
        'name': 'Team Creator',
        'description': 'Created your first hackathon team',
        'icon': '👑',
        'criteria': 'Create a team'
    },
    'team_joiner': {
        'name': 'Team Player',
        'description': 'Joined your first hackathon team',
        'icon': '🤝',
        'criteria': 'Join a team'
    },
    'active_leader': {
        'name': 'Active Leader',
        'description': 'Created 3 or more teams',
        'icon': '⭐',
        'criteria': 'Create 3 teams'
    },
    'quick_joiner': {
        'name': 'Quick Joiner',
        'description': 'Joined a team within 24 hours of its creation',
        'icon': '⚡',
        'criteria': 'Join a team within 24 hours of creation'
    },
    'veteran_hacker': {
        'name': 'Veteran Hacker',
        'description': 'Participated in 5 different hackathon teams',
        'icon': '🏆',
        'criteria': 'Join 5 different teams'
    }
}

def initialize_badges():
    """Initialize badge definitions in the database"""
    for badge_id, badge_info in BADGES.items():
        existing_badge = db_session.query(Badge).filter_by(name=badge_info['name']).first()
        if not existing_badge:
            badge = Badge(
                name=badge_info['name'],
                description=badge_info['description'],
                icon=badge_info['icon'],
                criteria=badge_info['criteria']
            )
            db_session.add(badge)
    db_session.commit()

def award_badge(user_id: int, badge_name: str) -> bool:
    """Award a badge to a user if they don't already have it"""
    badge = db_session.query(Badge).filter_by(name=BADGES[badge_name]['name']).first()
    if not badge:
        return False

    existing_achievement = db_session.query(Achievement).filter_by(
        user_id=user_id, badge_id=badge.id
    ).first()

    if existing_achievement:
        return False

    achievement = Achievement(user_id=user_id, badge_id=badge.id)
    db_session.add(achievement)
    db_session.commit()
    return True

def check_and_award_badges(user_id: int) -> list:
    """Check and award any new badges a user has earned"""
    user = db_session.query(User).get(user_id)
    if not user:
        return []

    new_badges = []

    # Check Team Creator badge
    if db_session.query(Team).filter_by(leader_id=user.id).first():
        if award_badge(user.id, 'team_creator'):
            new_badges.append(BADGES['team_creator'])

    # Check Team Joiner badge
    if len(user.teams) > 0:
        if award_badge(user.id, 'team_joiner'):
            new_badges.append(BADGES['team_joiner'])

    # Check Active Leader badge
    if db_session.query(Team).filter_by(leader_id=user.id).count() >= 3:
        if award_badge(user.id, 'active_leader'):
            new_badges.append(BADGES['active_leader'])

    # Check Quick Joiner badge
    # Query the team_members association table directly
    stmt = select(team_members.c.joined_at, Team.created_at).join(
        Team, team_members.c.team_id == Team.id
    ).where(team_members.c.user_id == user.id)

    for result in db_session.execute(stmt):
        if (result.joined_at - result.created_at) <= timedelta(days=1):
            if award_badge(user.id, 'quick_joiner'):
                new_badges.append(BADGES['quick_joiner'])
                break

    # Check Veteran Hacker badge
    if len(user.teams) >= 5:
        if award_badge(user.id, 'veteran_hacker'):
            new_badges.append(BADGES['veteran_hacker'])

    return new_badges

def get_user_badges(user_id: int) -> list:
    """Get all badges earned by a user"""
    achievements = db_session.query(Achievement).filter_by(user_id=user_id).all()
    return [achievement.badge for achievement in achievements]