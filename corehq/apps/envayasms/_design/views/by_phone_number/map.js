function (doc) {
	if (doc.doc_type == 'EnqueuedMessage') {
		emit(doc.phone_number, null);
	}
}