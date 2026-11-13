#!/usr/bin/env python3
"""Check Knowledge Base ingestion status."""

import boto3
import sys

KB_ID = "LGKVLOAVEZ"
DATA_SOURCE_ID = "49WWRDPPPM"
JOB_ID = "OYCQ8K8ENV"

def check_status():
    client = boto3.client('bedrock-agent')
    
    try:
        response = client.get_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=DATA_SOURCE_ID,
            ingestionJobId=JOB_ID
        )
        
        job = response['ingestionJob']
        stats = job['statistics']
        
        print("📊 Knowledge Base Ingestion Status")
        print("=" * 50)
        print(f"Status: {job['status']}")
        print(f"Documents Scanned: {stats['numberOfDocumentsScanned']}")
        print(f"Documents Indexed: {stats['numberOfNewDocumentsIndexed']}")
        print(f"Documents Failed: {stats['numberOfDocumentsFailed']}")
        print()
        
        if job['status'] == 'COMPLETE':
            print("✅ Ingestion COMPLETE!")
            print(f"   {stats['numberOfNewDocumentsIndexed']} PDFs indexed")
            print("\n🎉 Knowledge Base is ready!")
            print("   Generate questions now - they'll use your PDFs!")
            return True
        elif job['status'] == 'IN_PROGRESS':
            progress = (stats['numberOfNewDocumentsIndexed'] / stats['numberOfDocumentsScanned'] * 100) if stats['numberOfDocumentsScanned'] > 0 else 0
            print(f"⏳ Still processing... ({progress:.1f}% complete)")
            print("   This may take 5-10 minutes for 123 PDFs")
            return False
        else:
            print(f"⚠️  Status: {job['status']}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    check_status()
