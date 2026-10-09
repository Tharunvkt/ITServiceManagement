
from django import forms
from django.contrib.auth.models import User, Group
from .models import ServiceRequest, RequestComment


class ServiceRequestForm(forms.ModelForm):
    """Form for creating a new service request."""

    class Meta:
        model = ServiceRequest
        fields = [
            'title',
            'description',
            'category',
            'priority',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control'
            })

        self.fields['category'].widget.attrs.update({
            'class': 'form-select'
        })

        self.fields['priority'].widget.attrs.update({
            'class': 'form-select'
        })


class ServiceRequestUpdateForm(forms.ModelForm):
    """Form for assigning and updating an existing request."""

    note = forms.CharField(
        required=False,
        label='Update note',
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Explain the assignment or status change'
        })
    )

    class Meta:
        model = ServiceRequest
        fields = [
            'assigned_to',
            'status',
            'resolution_details',
        ]

        widgets = {
            'assigned_to': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'status': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'resolution_details': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Describe how the issue was resolved'
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        
        self.fields['assigned_to'].queryset = User.objects.filter(
    is_active=True,
    groups__name='Technician'
).distinct().order_by('username')
           

        self.fields['assigned_to'].required = False

    def clean(self):
        cleaned_data = super().clean()

        status = cleaned_data.get('status')
        resolution_details = cleaned_data.get(
            'resolution_details', ''
        )

        if status == 'Resolved' and not resolution_details.strip():
            self.add_error(
                'resolution_details',
                'Enter resolution details before resolving the request.'
            )

        
        if status == 'Closed':
            if self.instance.status != 'Resolved':
                self.add_error(
                    'status',
                    'Only resolved requests can be closed.'
                )

            if not resolution_details.strip():
                self.add_error(
                    'resolution_details',
                    'Resolution details are required before closing.'
                )


        return cleaned_data


class RequestCommentForm(forms.ModelForm):
    class Meta:
        model = RequestComment
        fields = ['message']
        labels = {
            'message': 'Add a comment or update',
        }
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your update here...',
            }),
        }

    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()

        if not message:
            raise forms.ValidationError(
                'Please enter a comment before submitting.'
            )

        return message

