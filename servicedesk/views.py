
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import (
    ServiceRequestForm,
    ServiceRequestUpdateForm,
    RequestCommentForm,
)
from .models import ServiceRequest, RequestHistory, RequestComment


# --------------------------------------------------
# ROLE HELPERS
# --------------------------------------------------

def is_manager(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name='Manager').exists()
    )


def is_technician(user):
    return user.is_authenticated and user.groups.filter(
        name='Technician'
    ).exists()


def is_requester(user):
    return user.is_authenticated and user.groups.filter(
        name='Requester'
    ).exists()


def is_it_staff(user):
    # Keep this helper for existing staff-only pages.
    return is_manager(user)


# --------------------------------------------------
# REQUEST LIST
# --------------------------------------------------

@login_required
def request_list(request):
    now = timezone.now()
    approaching_deadline = now + timedelta(hours=2)

    requests = ServiceRequest.objects.select_related(
        'category', 'created_by', 'assigned_to'
    ).order_by('-created_at')

    if is_manager(request.user):
        # Managers can see all requests.
        pass
    elif is_technician(request.user):
        # Technicians see only requests assigned to them.
        requests = requests.filter(assigned_to=request.user)
    else:
        # Requesters see only requests they created.
        requests = requests.filter(created_by=request.user)

    selected_status = request.GET.get('status', '')
    selected_priority = request.GET.get('priority', '')

    if selected_status:
        requests = requests.filter(status=selected_status)

    if selected_priority:
        requests = requests.filter(priority=selected_priority)

    overdue_count = requests.filter(
        sla_deadline__lt=now
    ).exclude(
        status__in=['Resolved', 'Closed']
    ).count()

    context = {
        'requests': requests,
        'approaching_deadline': approaching_deadline,
        'selected_status': selected_status,
        'selected_priority': selected_priority,
        'status_choices': ServiceRequest.STATUS_CHOICES,
        'priority_choices': ServiceRequest.PRIORITY_CHOICES,
        'now': now,
        'overdue_count': overdue_count,
    }

    return render(
        request,
        'servicedesk/request_list.html',
        context
    )


# --------------------------------------------------
# CREATE REQUEST
# --------------------------------------------------

@login_required
def request_create(request):
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST)

        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.created_by = request.user

            sla_hours = {
                'Critical': 4,
                'High': 8,
                'Medium': 24,
                'Low': 48,
            }

            service_request.sla_deadline = (
                timezone.now()
                + timedelta(hours=sla_hours[service_request.priority])
            )

            service_request.status = 'New'
            service_request.save()

            RequestHistory.objects.create(
                service_request=service_request,
                changed_by=request.user,
                old_status='',
                new_status='New',
                note='Request created'
            )

            messages.success(
                request,
                'Service request created successfully.'
            )

            return redirect(
                'request_detail',
                pk=service_request.pk
            )
    else:
        form = ServiceRequestForm()

    return render(
        request,
        'servicedesk/request_form.html',
        {'form': form}
    )


# --------------------------------------------------
# REQUEST DETAILS, COMMENTS AND HISTORY
# --------------------------------------------------

@login_required
def request_detail(request, pk):
    service_request = get_object_or_404(
        ServiceRequest.objects.select_related(
            'category', 'created_by', 'assigned_to'
        ),
        pk=pk
    )

    manager = is_manager(request.user)
    technician = is_technician(request.user)

    # Check who is allowed to view this request.
    if manager:
        pass
    elif technician:
        if service_request.assigned_to != request.user:
            messages.error(
                request,
                'You can only view requests assigned to you.'
            )
            return redirect('request_list')
    else:
        if service_request.created_by != request.user:
            messages.error(
                request,
                'You do not have permission to view this request.'
            )
            return redirect('request_list')

    # Handle comments.
    if request.method == 'POST':
        comment_form = RequestCommentForm(request.POST)

        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.service_request = service_request
            comment.author = request.user
            comment.save()

            messages.success(
                request,
                'Comment added successfully.'
            )

            return redirect(
                'request_detail',
                pk=service_request.pk
            )
    else:
        comment_form = RequestCommentForm()

    comments = service_request.comments.select_related(
        'author'
    ).order_by('-created_at')

    history = service_request.history.select_related(
        'changed_by'
    ).order_by('-changed_at')

    context = {
        'service_request': service_request,
        'comment_form': comment_form,
        'comments': comments,
        'history': history,
        'is_manager': manager,
        'is_technician': technician,
    }

    return render(
        request,
        'servicedesk/request_detail.html',
        context
    )


# --------------------------------------------------
# ASSIGN REQUEST / UPDATE STATUS
# --------------------------------------------------

@login_required
def request_update(request, pk):
    service_request = get_object_or_404(
        ServiceRequest,
        pk=pk
    )

    manager = is_manager(request.user)
    technician = is_technician(request.user)

    # Only Managers and Technicians can update requests.
    if not manager and not technician:
        messages.error(
            request,
            'You do not have permission to update this request.'
        )
        return redirect('request_list')

    # Technicians can only update their assigned requests.
    if technician and service_request.assigned_to != request.user:
        messages.error(
            request,
            'You can only update requests assigned to you.'
        )
        return redirect('request_list')

    # Technicians cannot update closed requests.
    if technician and service_request.status == 'Closed':
        messages.error(
            request,
            'Closed requests cannot be updated by Technicians.'
        )
        return redirect(
            'request_detail',
            pk=service_request.pk
        )

    def prepare_form(form):
        if technician:
            # Technicians cannot assign or reassign requests.
            form.fields.pop('assigned_to', None)

            # Technicians can update progress, but cannot close.
            form.fields['status'].choices = [
                choice
                for choice in ServiceRequest.STATUS_CHOICES
                if choice[0] in [
                    'Assigned',
                    'In Progress',
                    'On Hold',
                    'Resolved',
                ]
            ]

    if request.method == 'POST':
        old_status = service_request.status
        old_assigned_to = service_request.assigned_to

        form = ServiceRequestUpdateForm(
            request.POST,
            instance=service_request
        )
        prepare_form(form)

        if form.is_valid():
            updated_request = form.save(commit=False)

            # Automatically mark a newly assigned request as Assigned.
            if (
                manager
                and updated_request.assigned_to
                and updated_request.status == 'New'
            ):
                updated_request.status = 'Assigned'

            new_status = updated_request.status
            new_assigned_to = updated_request.assigned_to
            note = form.cleaned_data.get('note', '').strip()

            # Track when and by whom the request was resolved.
            if (
                old_status != 'Resolved'
                and new_status == 'Resolved'
            ):
                updated_request.resolved_at = timezone.now()
                updated_request.resolved_by = request.user

            elif (
                old_status == 'Resolved'
                and new_status != 'Resolved'
            ):
                updated_request.resolved_at = None
                updated_request.resolved_by = None

            history_notes = []

            if old_status != new_status:
                history_notes.append(
                    f'Status changed from {old_status} to {new_status}'
                )

            if old_assigned_to != new_assigned_to:
                if new_assigned_to:
                    history_notes.append(
                        f'Assigned to {new_assigned_to.username}'
                    )
                else:
                    history_notes.append('Request unassigned')

            if note:
                history_notes.append(note)

            updated_request.save()

            # Record status and assignment changes.
            if history_notes:
                RequestHistory.objects.create(
                    service_request=updated_request,
                    changed_by=request.user,
                    old_status=old_status,
                    new_status=new_status,
                    note=' | '.join(history_notes)
                )

            messages.success(
                request,
                'Service request updated successfully.'
            )

            return redirect(
                'request_detail',
                pk=updated_request.pk
            )

        messages.error(
            request,
            'Please correct the errors shown in the form.'
        )

    else:
        form = ServiceRequestUpdateForm(
            instance=service_request
        )
        prepare_form(form)

    return render(
        request,
        'servicedesk/request_update.html',
        {
            'form': form,
            'service_request': service_request,
        }
    )


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@login_required
def dashboard(request):
    requests = ServiceRequest.objects.all()

    if is_manager(request.user):
        pass
    elif is_technician(request.user):
        requests = requests.filter(assigned_to=request.user)
    else:
        requests = requests.filter(created_by=request.user)

    context = {
        'total_requests': requests.count(),
        'open_requests': requests.exclude(
            status__in=['Resolved', 'Closed']
        ).count(),
        'in_progress_requests': requests.filter(
            status='In Progress'
        ).count(),
        'resolved_requests': requests.filter(
            status='Resolved'
        ).count(),
        'closed_requests': requests.filter(
            status='Closed'
        ).count(),
    }

    return render(
        request,
        'servicedesk/dashboard.html',
        context
    )


# --------------------------------------------------
# REPORTS - MANAGERS ONLY
# --------------------------------------------------

@login_required
@user_passes_test(is_it_staff)
def reports(request):
    all_requests = ServiceRequest.objects.all()

    context = {
        'total_requests': all_requests.count(),
        'new_requests': all_requests.filter(status='New').count(),
        'assigned_requests': all_requests.filter(status='Assigned').count(),
        'in_progress_requests': all_requests.filter(
            status='In Progress'
        ).count(),
        'on_hold_requests': all_requests.filter(
            status='On Hold'
        ).count(),
        'resolved_requests': all_requests.filter(
            status='Resolved'
        ).count(),
        'closed_requests': all_requests.filter(status='Closed').count(),
        'unassigned_requests': all_requests.filter(
            assigned_to__isnull=True
        ).exclude(status__in=['Resolved', 'Closed']).count(),
        'breached_requests': all_requests.filter(
            sla_deadline__lt=timezone.now()
        ).exclude(status__in=['Resolved', 'Closed']).count(),
        'critical_requests': all_requests.filter(
            priority='Critical'
        ).count(),
        'high_requests': all_requests.filter(priority='High').count(),
        'medium_requests': all_requests.filter(
            priority='Medium'
        ).count(),
        'low_requests': all_requests.filter(priority='Low').count(),
    }

    return render(
        request,
        'servicedesk/reports.html',
        context
    )


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()

            # New registered users are Requesters by default.
            requester_group, _ = Group.objects.get_or_create(
                name='Requester'
            )
            user.groups.add(requester_group)

            messages.success(
                request,
                'Account created successfully! Please log in.'
            )

            return redirect('login')
    else:
        form = UserCreationForm()

    return render(
        request,
        'servicedesk/register.html',
        {'form': form}
    )
