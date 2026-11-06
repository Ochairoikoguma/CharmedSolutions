from django.db import models

class Client(models.Model):

    #client mapped to the existing Client table in db

    #db assigns the ID  when a new client is added
    client_id=models.AutoField(primary_key=True, db_column="ClientID")
    client_name=models.CharField(max_length=150, unique=True, db_column="ClientName")

    #New client cannot have a rate. 15.00 means 15%
    commission_rate= models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, db_column="CommissionRate")
    date_created=models.DateField(auto_now_add=True, db_column="DateCreated")

    class Meta:
        db_table="Client"
        managed=False

    def __str__(self):
        return self.client_name


class CollectionAccount(models.Model):

    #Simplicity collection account belonging to ONE client

    #db assigns internal ID. Slimplicity supplies account number
    account_id=models.AutoField(primary_key=True, db_column="AccountID")
    account_number=models.CharField(max_length=20, unique=True, db_column="AccountNumber")

    #ClientID column links account to its client
    client=models.ForeignKey(Client, on_delete=models.DO_NOTHING, db_column="ClientID", related_name="accounts",)

    debtor_name= models.CharField(max_length=150, db_column="DebtorName")

    class Meta:
        db_table="CollectionAccount"
        managed=False

    def __str__(self):
        return self.account_number

class Payment(models.Model):

    #Payment collected on a clients account

    payment_id= models.AutoField(primary_key=True, db_column="PaymentID")

    #AccountID links payment to the account it was collected on

    account= models.ForeignKey(CollectionAccount, on_delete=models.DO_NOTHING, db_column="AccountID", related_name="payments",)

    #use date payment was received
    payment_date= models.DateField(db_column="PaymentDate")

    #match db decimal so amount retains cents
    payment_amount= models.DecimalField(max_digits=12, decimal_places=2, db_column="PaymentAmount")

    class Meta:
        db_table="Payment"
        managed= False

class Cost(models.Model):
    #expense incurred on a collection account

    cost_id = models.AutoField(primary_key=True, db_column="CostID")

    #each cost belongs to one collection account
    account=models.ForeignKey(CollectionAccount, on_delete=models.DO_NOTHING, db_column="AccountID", related_name="costs",)

    #keep original expense date even if cost rolls over
    cost_date= models.DateField(db_column="CostDate")

    #new costs remain unbilled until included in remittance report
    billed = models.BooleanField(default=False, db_column="Billed")

    cost_description=models.CharField(max_length=255, null=True, blank=True, db_column="CostDescription")

    cost_amount=models.DecimalField(max_digits=12, decimal_places=2, db_column="CostAmount")

    #import sets this to the first day of the costs reporting month
    due_date= models.DateField(db_column="DueDate")

    class Meta:
        db_table = "Cost"
        managed = False

class Remittance(models.Model):
    #Clients monthly remittance totals and the PDF saved for report history
    remittance_id= models.AutoField(primary_key=True, db_column="RemittanceID")

    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, db_column="ClientID", related_name="remittances",)

    #use first day of reporting month, regardless of when PDF is created
    report_period= models.DateField(db_column="ReportPeriod")

    #store the amounts supplied by calculation service
    gross_recoveries = models.DecimalField(max_digits=12, decimal_places=2, db_column="GrossRecoveries")
    #save the rate used for this report
    commission_rate=models.DecimalField(max_digits=4, decimal_places=2, db_column="CommissionRate")
    total_commission= models.DecimalField(max_digits=12, decimal_places=2, db_column="TotalCommission")
    net_remittance= models.DecimalField(max_digits=12, decimal_places=2, db_column="NetRemittance")

    #store PDF bytes so staff can reopen original report from client history
    pdf_file= models.BinaryField(null=True, blank=True, db_column="PdfFile")

    class Meta:
        db_table="Remittance"
        managed = False
        unique_together= (("client", "report_period"),)    
