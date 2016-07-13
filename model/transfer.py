def equals(left, right):
	return (
		left and \
		right and \
		left['id'] == right['id'] and \
		left['amount'] == right['amount'] and \
		left['execution_condition'] == right['execution_condition'] and \
		left['cancellation_condition'] == right['cancellation_condition']
		)