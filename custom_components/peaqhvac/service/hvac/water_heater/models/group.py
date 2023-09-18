from custom_components.peaqhvac.service.models.enums.group_type import GroupType


class Group:
    def __init__(self, group_type: GroupType, hours: list[int]):
        self.group_type = group_type
        self.hours = hours