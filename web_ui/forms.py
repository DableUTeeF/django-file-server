from django import forms


class UploadFileForm(forms.Form):
    fileupload = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'onchange': "form.submit()",
            'title': 'File Upload',
            'value': "File Upload",
            'style': "display:none;",
            }
        )
    )

