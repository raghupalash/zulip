from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext as _

from zerver.decorator import require_member_or_admin
from zerver.lib.actions import check_add_realm_emoji, do_remove_realm_emoji
from zerver.lib.emoji import check_emoji_admin, check_valid_emoji_name
from zerver.lib.request import REQ, JsonableError, has_request_variables
from zerver.lib.response import json_success
from zerver.models import RealmEmoji, UserProfile


def list_emoji(request: HttpRequest, user_profile: UserProfile) -> HttpResponse:

    # We don't call check_emoji_admin here because the list of realm
    # emoji is public.
    return json_success({"emoji": user_profile.realm.get_emoji()})


@require_member_or_admin
@has_request_variables
def upload_emoji(
    request: HttpRequest, user_profile: UserProfile, emoji_name: str = REQ(path_only=True)
) -> HttpResponse:
    emoji_name = emoji_name.strip().replace(" ", "_")
    check_valid_emoji_name(emoji_name)
    check_emoji_admin(user_profile)
    if RealmEmoji.objects.filter(
        realm=user_profile.realm, name=emoji_name, deactivated=False
    ).exists():
        raise JsonableError(_("A custom emoji with this name already exists."))
    if len(request.FILES) != 1:
        raise JsonableError(_("You must upload exactly one file."))
    emoji_file = list(request.FILES.values())[0]
    if (settings.MAX_EMOJI_FILE_SIZE_MIB * 1024 * 1024) < emoji_file.size:
        raise JsonableError(
            _("Uploaded file is larger than the allowed limit of {} MiB").format(
                settings.MAX_EMOJI_FILE_SIZE_MIB,
            )
        )

    realm_emoji = check_add_realm_emoji(user_profile.realm, emoji_name, user_profile, emoji_file)
    if realm_emoji is None:
        raise JsonableError(_("Image file upload failed."))
    return json_success()


def delete_emoji(request: HttpRequest, user_profile: UserProfile, emoji_name: str) -> HttpResponse:
    if not RealmEmoji.objects.filter(
        realm=user_profile.realm, name=emoji_name, deactivated=False
    ).exists():
        raise JsonableError(_("Emoji '{}' does not exist").format(emoji_name))
    check_emoji_admin(user_profile, emoji_name)
    do_remove_realm_emoji(user_profile.realm, emoji_name)
    return json_success()
