from django import forms


class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField(label="Select a PDF file")

    def clean_pdf_file(self):
        pdf_file = self.cleaned_data["pdf_file"]
        if not pdf_file.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Please upload a valid .pdf file.")
        return pdf_file
