from datetime import date, timedelta

from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django import forms

from .models import Book, Author, BookInstance, Genre

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy



def index(request):
    """View function for home page of site."""
    
    num_books = Book.objects.count()
    num_instances = BookInstance.objects.count()
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()
    num_authors = Author.objects.count()

    # Contador de visitas do usuário
    num_visits = request.session.get('num_visits', 0)
    num_visits += 1
    request.session['num_visits'] = num_visits

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_visits': num_visits,
    }

    return render(request, 'index.html', context=context)


class BookListView(generic.ListView):
    model = Book
    paginate_by = 10


class BookDetailView(generic.DetailView):
    model = Book

class AuthorListView(generic.ListView):
    model = Author
    paginate_by = 10


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    """Lista livros emprestados ao usuário logado."""
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return (
            BookInstance.objects.filter(borrower=self.request.user)
            .filter(status__exact='o')  # 'o' = On loan
            .order_by('due_back')
        )


class LoanedBooksAllListView(PermissionRequiredMixin, generic.ListView):
    """Lista todos os livros emprestados (para bibliotecários)."""
    model = BookInstance
    permission_required = 'catalog.can_mark_returned'
    template_name = 'catalog/bookinstance_list_all_borrowed.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(status__exact='o').order_by('due_back')


class RenewBookForm(forms.Form):
    """Formulário para renovar um livro."""
    renewal_date = forms.DateField(
        help_text="Digite uma data entre hoje e 4 semanas a partir de hoje",
        initial=date.today() + timedelta(weeks=3)
    )

    def clean_renewal_date(self):
        data = self.cleaned_data['renewal_date']

        # Verifica se a data não está no passado
        if data < date.today():
            raise forms.ValidationError("Data inválida - não pode estar no passado")

        # Verifica se a data não ultrapassa 4 semanas à frente
        if data > date.today() + timedelta(weeks=4):
            raise forms.ValidationError("Data inválida - não pode ultrapassar 4 semanas a partir de hoje")

        return data


@permission_required('catalog.can_mark_returned')
def renew_book_librarian(request, pk):
    """Renovar um livro específico por um bibliotecário."""
    book_instance = get_object_or_404(BookInstance, pk=pk)

    if request.method == 'POST':
        form = RenewBookForm(request.POST)
        if form.is_valid():
            book_instance.due_back = form.cleaned_data['renewal_date']
            book_instance.save()
            return HttpResponseRedirect(reverse('all-borrowed'))
    else:
        proposed_date = date.today() + timedelta(weeks=3)
        form = RenewBookForm(initial={'renewal_date': proposed_date})

    context = {
        'form': form,
        'book_instance': book_instance,
    }

    return render(request, 'catalog/book_renew_librarian.html', context)

class AuthorCreate(PermissionRequiredMixin, CreateView):
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']
    initial = {'date_of_death': '11/11/2023'}
    permission_required = 'catalog.add_author'

class AuthorUpdate(PermissionRequiredMixin, UpdateView):
    model = Author
    # Not recommended (potential security issue if more fields added)
    fields = '__all__'
    permission_required = 'catalog.change_author'

class AuthorDelete(PermissionRequiredMixin, DeleteView):
    model = Author
    success_url = reverse_lazy('authors')
    permission_required = 'catalog.delete_author'

    def form_valid(self, form):
        try:
            self.object.delete()
            return HttpResponseRedirect(self.success_url)
        except Exception as e:
            return HttpResponseRedirect(
                reverse("author-delete", kwargs={"pk": self.object.pk})
            )

class AuthorDetailView(generic.DetailView):
    model = Author