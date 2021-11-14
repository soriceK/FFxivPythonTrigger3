from functools import cached_property, lru_cache, cache
from math import sqrt

from FFxivPythonTrigger.saint_coinach import action_sheet

from . import api, define, utils
from .strategies import UseAbility

invincible_effects = {325, 394, 529, 656, 671, 775, 776, 895, 969, 981, 1570, 1697, 1829, 1302, }
invincible_actor = set()

test_enemy_action = 9
test_enemy_pvp_action = 8746


def is_actor_status_can_damage(actor):
    if actor.id in invincible_actor or not actor.can_select:
        return False
    for eid, _ in actor.effects.get_items():
        if eid in invincible_effects:
            return False
    return True


class LogicData(object):
    def __init__(self, config: dict):
        self.config = config
        self.ability_cnt = 0

    @cached_property
    def me(self):
        return api.get_me_actor()

    @cached_property
    def job(self):
        return utils.job_name()

    @cached_property
    def target_check_action(self):
        return test_enemy_pvp_action if self.is_pvp else test_enemy_action

    @lru_cache
    def is_target_attackable(self, target_actor):
        return (is_actor_status_can_damage(target_actor) and
                api.action_type_check(self.target_check_action, target_actor) and
                target_actor.current_hp > 1)

    @cached_property
    def target(self):
        for method in self.config['target_priority']:
            t = self.get_target(method)
            if t is not None and self.is_target_attackable(t):
                return t

    @lru_cache
    def get_target(self, method: str):
        match method:
            case define.CURRENT_SELECTED:
                return api.get_current_target()
            case define.FOCUSED:
                return api.get_focus_target()
            case define.DISTANCE_NEAREST:
                return min(self.valid_enemies,key = self.actor_distance_effective)
            case define.DISTANCE_FURTHEST:
                return max(self.valid_enemies,key = self.actor_distance_effective)
            case define.HP_HIGHEST:
                return max(self.valid_enemies,key = lambda x: x.current_hp)
            case define.HP_LOWEST:
                return min(self.valid_enemies,key = lambda x: x.current_hp)
            case define.HPP_HIGHEST:
                return max(self.valid_enemies,key = lambda x: x.current_hp / x.max_hp)
            case define.HPP_LOWEST:
                return min(self.valid_enemies,key = lambda x: x.current_hp / x.max_hp)

    @cached_property
    def valid_party(self):
        return [actor for actor in api.get_party_list() if actor.can_select]

    @cached_property
    def valid_alliance(self):
        return [actor for actor in api.get_party_list(True) if actor.can_select]

    @cached_property
    def valid_players(self):
        return [actor for actor in self.all_actors if actor.type == 1]

    @cached_property
    def all_actors(self):
        return api.get_can_select()

    @cache
    def target_action_check(self, action_id, target):
        """
        ray check if you can use the action on target (not checking actor type!)
        :param action_id: the action id check
        :param target: the target actor
        :return: if action can use
        """
        o = self.me.pos.r
        self.me.pos.r = self.me.target_radian(target)
        ans = not api.action_distance_check(action_id, self.me, target)
        self.me.pos.r = o
        return ans

    @cached_property
    def valid_enemies(self):
        """
        all actors select from enemy list, and if enable extra_enemies, also search in actor table
        :return: list of enemy actor sorted by distance
        """
        match self.config['targets']:
            case define.ONLY_SELECTED:
                current = api.get_current_target()
                all_enemy = [] if current is None or not self.is_target_attackable(current) else [current]
            case define.ENEMY_LIST:
                all_enemy = [actor for actor in api.get_enemies_list() if self.is_target_attackable(actor)]
            case define.ALL_IN_COMBAT | define.ALL_CAN_ATTACK as k:
                all_enemy = [actor for actor in api.get_can_select() if self.is_target_attackable(actor)]
                if k == define.ALL_IN_COMBAT:
                    all_enemy = [actor for actor in all_enemy if actor.is_in_combat]
            case k:
                raise Exception(f'invalid targets {k}')
        return sorted(all_enemy, key=self.actor_distance_effective)

    # @lru_cache
    # def dps(self, actor_id):
    #     """
    #     get dps of an actor
    #     """
    #     return api.get_actor_dps(actor_id)
    #
    # @lru_cache
    # def tdps(self, actor_id):
    #     """
    #     get tdps of an actor
    #     """
    #     return api.get_actor_tdps(actor_id)
    #
    # @lru_cache
    # def ttk(self, actor_id):
    #     """
    #     get time to kill of an actor
    #     """
    #     t = api.get_actor_by_id(actor_id)
    #     if t is None:
    #         return -1
    #     else:
    #         tdps = self.tdps(actor_id)
    #         return (t.currentHP / tdps) if tdps else 1e+99
    # @property
    # def time_to_kill_target(self):
    #     """
    #     the time to kill of chosen target
    #     """
    #     if self.target is None: return 1e+99
    #     return self.ttk(self.target.id)
    #
    # @cached_property
    # def max_ttk(self):
    #     """
    #     the largest time to kill in valid enemies
    #     """
    #     if not len(self.valid_enemies): return 1e+99
    #     return max(self.ttk(e.id) for e in self.valid_enemies)

    @cached_property
    def combo_state(self):
        return api.get_combo_state()

    @property
    def combo_id(self):
        return self.combo_state.action_id

    @property
    def combo_remain(self):
        return self.combo_state.remain

    @cached_property
    def effects(self):
        return self.me.effects.get_dict()

    @cached_property
    def gauge(self):
        return api.get_gauge()

    @cached_property
    def gcd_group(self):
        return api.get_global_cool_down_group()

    @property
    def gcd(self):
        return self.gcd_group.remain

    @property
    def gcd_total(self):
        return self.gcd_group.total

    def reset_cd(self, action_id: int):
        """
        reset the cd of a skill (just in client!)
        """
        api.reset_cd(action_sheet[action_id]['CooldownGroup'])

    @cache
    def skill_cd(self, action_id: int):
        """remain time of an action cool down"""

        row = action_sheet[action_id]
        if self.me.level < row['ClassJobLevel']:
            return 1e+99
        else:
            return api.get_cd_group(row['CooldownGroup']).remain

    @cache
    def pvp_skill_cd(self, action_id: int):
        """remain time of an pvp action cool down"""

        gp = api.pvp_action_cd_group_id(action_id)
        if gp:
            return api.get_cd_group(gp).remain
        else:
            return 1e+99

    def __getitem__(self, item):
        return self.skill_cd(item)

    @lru_cache
    def item_count(self, item_id, is_hq: bool = None):
        """count items in backpack"""
        return api.get_backpack_item_count(item_id, is_hq)

    @cached_property
    def is_moving(self):
        """if user is moving"""
        match self.config['cast_move']:
            case define.ALWAYS_CASTING:
                return False
            case define.ALWAYS_MOVING:
                return True
            case _:
                return bool(api.get_movement_speed())

    @lru_cache
    def actor_distance_effective(self, target_actor):
        """effective distance between user and a target"""
        if self.config['use_builtin_effective_distance']:
            return target_actor.effectiveDistanceX
        else:
            t_pos = target_actor.pos
            m_pos = self.coordinate
            return max(sqrt((t_pos.x - m_pos.x) ** 2 + (t_pos.y - m_pos.y) ** 2) - self.me.hitbox_radius - target_actor.hitbox_radius, 0)

    @cached_property
    def target_distance(self):
        t = self.target
        if t is None: return 1e+99
        return self.actor_distance_effective(t)

    @cached_property
    def coordinate(self):
        return api.get_coordinate()

    @cached_property
    def is_pvp(self):
        return utils.is_pvp()

    def use_ability_to_target(self, ability_id):
        return UseAbility(ability_id, (self.target.id if self.target is not None else self.me.id))
