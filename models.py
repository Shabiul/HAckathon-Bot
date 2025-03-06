from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from app import Base

# Association table for team members
team_members = Table(
    'team_members',
    Base.metadata,
    Column('team_id', Integer, ForeignKey('team.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('joined_at', DateTime, default=datetime.utcnow)
)

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(64), unique=True, nullable=False)
    username = Column(String(128), nullable=False)
    teams = relationship('Team', secondary=team_members, back_populates='members')
    achievements = relationship('Achievement', back_populates='user')

class Team(Base):
    __tablename__ = 'team'
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    hackathon_id = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    leader_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    members = relationship('User', secondary=team_members, back_populates='teams')
    description = Column(Text)

class Badge(Base):
    __tablename__ = 'badge'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    description = Column(String(256), nullable=False)
    icon = Column(String(64), nullable=False)
    criteria = Column(String(256), nullable=False)

class Achievement(Base):
    __tablename__ = 'achievement'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    badge_id = Column(Integer, ForeignKey('badge.id'), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)
    user = relationship('User', back_populates='achievements')
    badge = relationship('Badge')