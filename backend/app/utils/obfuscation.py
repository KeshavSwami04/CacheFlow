"""
64-bit Feistel Cipher for ID permutation.

Provides bijective (1-to-1) mapping of sequential IDs to pseudo-random integers.
This ensures generated short codes look randomized and are non-guessable,
without requiring database collision lookup loops.
"""

def permute_id(val: int) -> int:
    """
    Bijectively maps a 64-bit integer to a pseudo-random 64-bit integer.
    Guarantees no collisions.
    """
    # Ensure inputs fit within 64-bit unsigned space
    val = val & 0xFFFFFFFFFFFFFFFF
    
    # Split into 32-bit halves
    L = val & 0xFFFFFFFF
    R = (val >> 32) & 0xFFFFFFFF
    
    # 4 rounds of Feistel
    # Round keys derived from arbitrary hex digits
    round_keys = [0x243F6A88, 0x85A308D3, 0x13198A2E, 0x03707344]
    
    for round_key in round_keys:
        # Simple, non-linear round function: F(R, K)
        # Multiply by a prime number and XOR with round key
        f_val = ((R ^ round_key) * 0x45197F37) & 0xFFFFFFFF
        temp = L ^ f_val
        L = R
        R = temp
        
    # Combine halves
    result = (R << 32) | L
    return result & 0xFFFFFFFFFFFFFFFF


def unpermute_id(val: int) -> int:
    """
    Reverses the bijective mapping of permute_id.
    """
    val = val & 0xFFFFFFFFFFFFFFFF
    R = (val >> 32) & 0xFFFFFFFF
    L = val & 0xFFFFFFFF
    
    # Reversed round keys
    round_keys = [0x03707344, 0x13198A2E, 0x85A308D3, 0x243F6A88]
    
    for round_key in round_keys:
        f_val = ((L ^ round_key) * 0x45197F37) & 0xFFFFFFFF
        temp = R ^ f_val
        R = L
        L = temp
        
    result = (R << 32) | L
    return result & 0xFFFFFFFFFFFFFFFF
