from typing import TYPE_CHECKING, Tuple

from FFxivPythonTrigger.utils.shape import sector, circle, rotated_rect

from .logic_data import LogicData

if TYPE_CHECKING:
    from XivMemory.struct.actor import Actor
    from shapely import geometry


class AbilityType(object):
    type = -1

    def is_valid_target(self, data: LogicData, target: 'Actor') -> bool:
        pass

    def aoe_shape(self, data: LogicData, target: 'Actor') -> 'geometry.Polygon':
        pass


class NearCircle(AbilityType):
    type = 0

    def __init__(self, radius: float, ):
        self.radius = radius

    def is_valid_target(self, data: LogicData, target: 'Actor') -> bool:
        return data.me.absolute_distance_xy(target) < self.radius + target.hitbox_radius

    def aoe_shape(self, data: LogicData, target: 'Actor') -> 'geometry.Polygon':
        return circle(data.me.pos.x, data.me.pos.y, self.radius)


class Sector(AbilityType):
    type = 3

    def __init__(self, a_range: int, angle: float):
        self.a_range = a_range
        self.angle = angle

    def is_valid_target(self, data: LogicData, target: 'Actor'):
        return data.me.absolute_distance_xy(target) < self.a_range + target.hitbox_radius

    def aoe_shape(self, data: LogicData, target: 'Actor') -> 'geometry.Polygon':
        return sector(data.me.pos.x, data.me.pos.y, self.a_range, self.angle, data.me.target_radian(target))


class FarCircle(AbilityType):
    type = 1

    def __init__(self, a_range: int, radius: float):
        self.a_range = a_range
        self.radius = radius

    def is_valid_target(self, data: LogicData, target: 'Actor'):
        return data.actor_distance_effective(target) < self.a_range

    def aoe_shape(self, data: LogicData, target: 'Actor') -> 'geometry.Polygon':
        return circle(target.pos.x, target.pos.y, self.radius)


class Rectangle(AbilityType):
    type = 2

    def __init__(self, a_range: int, width: float):
        self.a_range = a_range
        self.width = width

    def is_valid_target(self, data: LogicData, target: 'Actor'):
        return data.me.absolute_distance_xy(target) < self.a_range + target.hitbox_radius

    def aoe_shape(self, data: LogicData, target: 'Actor') -> 'geometry.Polygon':
        return rotated_rect(data.me.pos.x, data.me.pos.y, self.width, self.a_range, data.me.target_radian(target))


class Enemy(object):
    def __init__(self, data: LogicData, target: 'Actor', ability: AbilityType):
        self.target = target
        self.hit_box = target.hitbox()
        self.can_hit = ability.is_valid_target(data, target)
        self.aoe_shape = ability.aoe_shape(data, target) if self.can_hit else None
        self.calc_targets = 0

    def calc(self, enemies: list['Enemy']):
        if self.can_hit:
            self.calc_targets = sum(self.aoe_shape.intersects(enemy.hit_box) for enemy in enemies)
        else:
            self.calc_targets = 0
        return self.calc_targets


def select(data: LogicData, valid_enemies: list['Actor'], ability: AbilityType) -> Tuple['Actor|None', int]:
    if not valid_enemies: return None, 0
    if ability.type:
        enemies = [Enemy(data, target, ability) for target in valid_enemies]
        selected = max(enemies, key=lambda enemy: enemy.calc(enemies))
        return selected.target, selected.calc_targets
    else:
        aoe = ability.aoe_shape(data, data.target)
        return data.target, sum(aoe.intersects(enemy.hitbox()) for enemy in valid_enemies)
