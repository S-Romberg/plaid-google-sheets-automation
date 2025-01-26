from flask import Flask, request
import functions_framework
from google.cloud import secretmanager
import json
import hmac
import hashlib
from plaid_sync import PlaidTransactionSync
from sheets_sync import SheetsSyncer

def get_secret(secret_id):
    """Retrieve secret from Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/YOUR_PROJECT_ID/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

@functions_framework.http
def webhook_handler(request):
    """Handle Plaid webhooks"""
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405

    # Verify webhook signature
    try:
        verify_webhook_signature(request)
    except ValueError as e:
        return str(e), 401

    webhook_data = request.get_json()
    webhook_type = webhook_data.get('webhook_type')
    webhook_code = webhook_data.get('webhook_code')

    # Log webhook for debugging
    print(f"Received webhook: {webhook_type} - {webhook_code}")

    if webhook_type == 'TRANSACTIONS' and webhook_code == 'SYNC_UPDATES_AVAILABLE':
        try:
            # Get the item_id from the webhook
            item_id = webhook_data.get('item_id')
            
            # Initialize syncers
            syncer = SheetsSyncer()
            
            # Get access token for this item_id from Secret Manager
            access_token = get_secret(f"plaid-access-token-{item_id}")
            
            # Sync transactions
            transactions = syncer.plaid_syncer.sync_transactions(access_token)
            syncer.append_transactions(transactions)
            
            return {
                'success': True,
                'message': f'Processed {len(transactions)} transactions'
            }
        except Exception as e:
            print(f"Error processing webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    return {
        'success': True,
        'message': 'Webhook received but no action needed'
    }

def verify_webhook_signature(request):
    """Verify that the webhook is from Plaid"""
    plaid_signature = request.headers.get('Plaid-Verification')
    if not plaid_signature:
        raise ValueError('No Plaid signature found')

    webhook_secret = get_secret('plaid-webhook-secret')
    body = request.get_data().decode('utf-8')
    
    calculated_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_signature, plaid_signature):
        raise ValueError('Invalid webhook signature')