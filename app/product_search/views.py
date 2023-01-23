from django.shortcuts import render
from django.views.generic import TemplateView


class SearchProduct(TemplateView):
    template_name = "index.html"

    def get(self, request):
        # if request.user.id == id or request.user.has_perm("permissions.users.index"):
        #     profile_data = UserProfile.profile_information(id=id)
        return render(request, self.template_name)

    def post(self, request):
        return render(request, self.template_name)
