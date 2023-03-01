from django.shortcuts import render
from app.login.models import UserProfile, Direction
from django.http import HttpResponseRedirect
from django.core.exceptions import BadRequest
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView
from app.login.form import CustomAuthenticationForm
from app.common.decorators import permission_required
from django.contrib.auth.models import Group, Permission
from app.login.serializers import ProfileSerializer, GroupDirectionSerializer


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = CustomAuthenticationForm


class Profile(TemplateView):
    template_name = "profile/profile.html"

    def get(self, request, id):
        if request.user.id == id or request.user.has_perm("permissions.users.index"):
            profile_data = UserProfile.profile_information(id=id)
            return render(request, self.template_name, context=profile_data)


class EditProfile(TemplateView):
    template_name = "profile/edit_profile.html"

    @permission_required('permissions.users.edit')
    def get(self, request, id):
        profile_data = UserProfile.profile_information(id=id)
        groups = Group.objects.all()
        groups = GroupDirectionSerializer(data=groups)
        groups.serialize()
        directions = Direction.objects.all()
        directions = GroupDirectionSerializer(data=directions)
        directions.serialize()
        all_groups_direction = {
            "all_groups": groups.to_dict,
            "all_directions": directions.to_dict
        }

        return render(request, self.template_name, context=profile_data | all_groups_direction)

    @permission_required('permissions.users.edit')
    def post(self, request, id):
        user = UserProfile.objects.get(id=id)
        new_user_groups = [int(group) for group in request.POST.getlist('groups[]')]
        user.groups.clear()
        user.groups.add(*new_user_groups)
        new_user_directions = [int(group) for group in request.POST.getlist('directions[]')]
        user.direction.clear()
        user.direction.add(*new_user_directions)
        return HttpResponseRedirect(f"/accounts/profile/{id}/")
