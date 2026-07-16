$ORIGIN omarchaconart.com.
$TTL 3600
@   IN SOA ns1.thehappyendings.org. hostmaster.thehappyendings.org. (
        2026070201 ; serial
        7200 3600 1209600 3600 )
@       IN NS    ns1.thehappyendings.org.
@       IN NS    ns2.thehappyendings.org.
@       IN A     72.60.117.113
@       IN AAAA  2a02:4780:2d:f957::1
www     IN A     72.60.117.113
www     IN AAAA  2a02:4780:2d:f957::1
