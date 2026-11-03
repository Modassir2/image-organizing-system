Classify the attached image by deciding whether it is a document or not a document.

Use exactly one of the allowed categories below. The category value must match the tool enum exactly, including spelling:

- `important_documents`: identity documents, passports, licenses, certificates, receipts, invoices, financial records, or other documents that are likely important to keep.
- `medical_documents`: prescriptions, medical reports, lab results, health records, doctor notes, or other healthcare documents.
- `legal_documents`: contracts, court papers, legal notices, deeds, wills, or other legal documents.
- `other_documents`: a document that does not fit the medical or legal categories and is not clearly an important document.
- `not_documents`: photographs, screenshots without document-like content, artwork, scenery, objects, people, animals, or any other image that is not primarily a document.

Decide from the visible content only. If an image contains a document, classify the document by its main purpose. If the image only contains a photograph of a person, place, object, or scene, use `not_documents`. If a document could fit multiple document categories, choose the most specific category. Do not invent a category or change the spelling of a category.

Return the result only through the required `sort_image` tool call.